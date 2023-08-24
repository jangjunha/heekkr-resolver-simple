import abc
import logging
import re
import urllib.parse
import itertools
from io import BytesIO
from typing import AsyncIterable, Iterable

from aiocache import cached
from aiohttp import ClientSession
from bs4 import BeautifulSoup, Tag
from heekkr.book_pb2 import Book, PublishDate
from heekkr.common_pb2 import Date, DateTime
from heekkr.holding_pb2 import (
    HoldingSummary,
    HoldingStatus,
    AvailableStatus,
    UnavailableStatus,
    OnLoanStatus,
)
from heekkr.resolver_pb2 import SearchEntity
from multidict import MultiDict
from openpyxl.reader.excel import load_workbook

from app.core import Coordinate, Library
from app.utils.kakao import Kakao
from app.utils.text import select_closest


logger = logging.getLogger(__name__)


class JnetSplibSearcher(metaclass=abc.ABCMeta):
    @property
    @abc.abstractmethod
    def id_prefix(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def url_base(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def path_search_index(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def path_search(self) -> str:
        ...

    @property
    def path_export_excel(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def path_book_detail(self) -> str:
        ...

    @property
    def export_available(self) -> bool:
        try:
            _ = self.path_export_excel
            return True
        except NotImplementedError:
            return False

    def normalize_library_name(self, name: str) -> str:
        return name

    def transform_library_name_for_search(self, name: str) -> str:
        return name

    async def get_libraries_response(self) -> str:
        async with ClientSession(self.url_base) as session, session.get(
            self.path_search_index
        ) as response:
            return await response.text()

    @cached(ttl=60 * 60 * 24)
    async def get_libraries(self) -> Iterable[Library]:
        text = await self.get_libraries_response()
        soup = BeautifulSoup(text, "lxml")
        res = []
        async with Kakao() as kakao:
            for li in itertools.chain(
                soup.select("#contents .searchCheckBox ul > li"),
                soup.select("#contents ol.finder_lib > li"),
            ):
                name = self.normalize_library_name(li.text.strip())
                if input := li.select_one("input[type=checkbox]"):
                    key = input.attrs["value"]
                    if key == "ALL":
                        continue
                    coordinate = None
                    if address := await kakao.search_keyword(
                        self.transform_library_name_for_search(name)
                    ):
                        coordinate = Coordinate(latitude=address.y, longitude=address.x)
                    res.append(
                        Library(
                            id=f"{self.id_prefix}{key}",
                            name=name,
                            coordinate=coordinate,
                        )
                    )
        return res

    async def map_library_to_searchkey(self, library_id: str) -> str:
        return library_id.removeprefix(self.id_prefix)

    def search_query(self, keyword: str, library_keys: Iterable[str]) -> MultiDict:
        query = MultiDict(
            [
                ("searchType", "SIMPLE"),
                ("searchKey", "ALL"),
                ("searchKeyword", keyword),
                *(("searchLibraryArr", key) for key in library_keys),
            ]
        )
        logger.debug(f"search query {query!r}")
        return query

    async def search_response(self, keyword: str, library_ids: Iterable[str]) -> str:
        library_search_keys = [
            await self.map_library_to_searchkey(lid) for lid in library_ids
        ]
        async with ClientSession(self.url_base) as session, session.post(
            self.path_search,
            data=self.search_query(keyword, library_search_keys),
        ) as response:
            return await response.text()

    async def search(
        self,
        keyword: str,
        library_ids: Iterable[str],
    ) -> AsyncIterable[SearchEntity]:
        text = await self.search_response(keyword, library_ids)
        soup = BeautifulSoup(text, "lxml")
        results = soup.select(
            "#contents .bookList > ul > "
            "li:not(.emptyNote):not(.noResultNote):not(.message)"
        )
        logger.debug(f"search result length = {len(results)}")
        if len(results) == 0:
            return

        # Case #1
        if self.export_available:
            books = []
            for li in results:
                if book_id := self.parse_id(li):
                    books.append(
                        {
                            "id": book_id,
                            "args": {
                                "entity": {
                                    "url": self.parse_url(li),
                                },
                                "book": {},
                                "holding_summary": {
                                    "status": self.parse_status(li),
                                },
                            },
                        }
                    )
            if books:
                async for entity in self.export(books):
                    yield entity
                return

        # Fallback
        for li in results:
            library, location = await self.parse_library(li)
            yield SearchEntity(
                book=Book(
                    isbn=self.parse_isbn(li),
                    title=self.parse_title(li),
                    author=self.parse_author(li),
                    publisher=self.parse_publisher(li),
                    publish_date=self.parse_publish_date(li),
                ),
                holding_summaries=[
                    HoldingSummary(
                        library_id=library.id,
                        location=location,
                        call_number=self.parse_call_number(li),
                        status=self.parse_status(li),
                    )
                ],
                url=self.parse_url(li),
            )

    async def export_to_excel_response(
        self, infos: Iterable[dict]
    ) -> Iterable[Iterable] | None:
        try:
            path = self.path_export_excel
        except NotImplementedError:
            return None
        async with ClientSession(self.url_base) as session, session.post(
            path,
            params=[("check", info["id"]) for info in infos],
        ) as response:
            if response.ok:
                ws = load_workbook(
                    BytesIO(await response.content.read()), data_only=True
                ).active
                return ws.values

    async def export(
        self,
        infos: Iterable[dict],
    ) -> AsyncIterable[SearchEntity]:
        if res := await self.export_to_excel_response(infos):
            header, *data = res
        else:
            return

        if header is None:
            logger.warning("Cannot export")
            return

        def find_index(*candidates: Iterable[str]) -> int:
            for c in candidates:
                if c in header:
                    return header.index(c)
            raise NotImplementedError(f"Cannot find {candidates=}")

        i_title = find_index("서명")
        i_author = find_index("저자")
        i_publisher = find_index("출판사", "발행자")
        i_publish_year = find_index(
            "발행년",
            "출판년도",
            "출판연도",
            "발행년도",
            "발행연도",
        )
        i_call_number = find_index("청구기호")
        i_isbn = find_index("ISBN", "표준번호(ISBN, ISSN)")
        i_library = find_index("도서관")
        i_location = find_index("자료실", "자료실명")

        for parts, info in zip(data, infos):

            def get(i: int) -> str | None:
                return parts[i] if parts[i] != "-" else None

            isbn = get(i_isbn)
            if isbn is None:
                logger.warning("Cannot parse ISBN", extra={"parts": parts})
                continue

            publish_year = get(i_publish_year)
            publish_year = int(publish_year) if publish_year else None

            args = info["args"]
            yield SearchEntity(
                book=Book(
                    isbn=isbn,
                    title=get(i_title),
                    author=get(i_author),
                    publisher=get(i_publisher),
                    publish_date=(
                        PublishDate(year=publish_year) if publish_year else None
                    ),
                    **args["book"],
                ),
                holding_summaries=[
                    HoldingSummary(
                        library_id=select_closest(
                            [(lib, lib.name) for lib in await self.get_libraries()],
                            get(i_library),
                        ).id,
                        location=get(i_location),
                        call_number=get(i_call_number),
                        **args["holding_summary"],
                    )
                ],
                **args["entity"],
            )

    def parse_id(self, root: Tag) -> str:
        return "^".join(self.parse_id_from_url(root))

    def parse_id_from_url(self, root: Tag) -> tuple[str, str, str] | None:
        for elem in root.select("a"):
            if m := URL_PATTERN.search(elem.attrs["onclick"]):
                return m.group(1), m.group(2), m.group(3)

    def parse_url(self, root: Tag) -> str | None:
        if m := self.parse_id_from_url(root):
            rec_key, book_key, publish_form_code = m
            parts = list(
                urllib.parse.urlparse(
                    urllib.parse.urljoin(self.url_base, self.path_book_detail)
                )
            )
            parts[4] = urllib.parse.urlencode(
                {
                    "recKey": rec_key,
                    "bookKey": book_key,
                    "publishFormCode": publish_form_code,
                }
            )
            return urllib.parse.urlunparse(parts)

    def parse_title(self, root: Tag) -> str | None:
        if elem := root.select_one(".book_name .title"):
            if m := TITLE_PATTERN.match(elem.text):
                return m.group(1)
        logger.warn("Cannot parse title")

    def parse_isbn(self, root: Tag) -> str | None:
        if a := root.select_one(".bookDetailInfo a.btn_haveinfo"):
            if m := ISBN_PATTERN.match(a.attrs["onclick"]):
                return m.group(1)
        logger.warn("Cannot parse isbn")

    def parse_author(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info01"):
            return elem.text.strip()
        logger.warn("Cannot parse author")

    def parse_publisher(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                return children[0].text.strip()
        logger.warn("Cannot parse publisher")

    def parse_publish_date(self, root: Tag) -> PublishDate | None:
        if elem := root.select_one(".bookData .book_info.info02"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 2:
                year_str = children[1].text.strip()
                try:
                    year = int(year_str)
                except ValueError:
                    logger.warn("Cannot parse publish year to integer")
                    return
                return PublishDate(year=year)
        logger.warn("Cannot parse publish date")

    async def parse_library(self, root: Tag) -> tuple[Library, str | None]:
        if elem := root.select_one(".bookData .book_info.info03"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                libraries = list(await self.get_libraries())
                library_str = children[0].text.strip()
                library = select_closest(
                    [(lib, lib.name) for lib in libraries],
                    library_str,
                )
            else:
                raise RuntimeError("Cannot parse library_str")
            if len(children) >= 2:
                location = children[1].text.strip()
            else:
                location = None
                logger.warn("Cannot parse location")
            return library, location
        raise RuntimeError("Cannot parse library")

    def parse_call_number(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 3:
                return children[2].text.strip()
        logger.warn("Cannot parse call number")

    def parse_requests_available(self, root: Tag) -> bool:
        for elem in root.select(".bookBtnWrap a"):
            if onclick := elem.attrs.get("onclick"):
                if "fnLoanReservationApplyProc" in onclick:
                    return True
        return False

    def parse_status(
        self,
        root: Tag,
    ) -> HoldingStatus | None:
        if elem := root.select_one(".bookData .status"):
            text = elem.text.strip()
            if m := STATUS_PATTERN.search(text):
                status_text = m.group(1)
                detail = m.group(2).strip("[]()")
                requests_available = self.parse_requests_available(root)
                waitings, _, due = self.parse_loan_status(root)
                if status_text == "대출가능":
                    return HoldingStatus(
                        available=AvailableStatus(detail=detail),
                        is_requested=waitings > 0 if waitings else False,
                        requests=waitings,
                        requests_available=requests_available,
                    )
                elif status_text == "대출불가":
                    if detail == "대출중":
                        return HoldingStatus(
                            on_loan=OnLoanStatus(due=due),
                            is_requested=waitings > 0 if waitings else False,
                            requests=waitings,
                            requests_available=requests_available,
                        )
                    else:
                        return HoldingStatus(
                            unavailable=UnavailableStatus(detail=detail),
                            is_requested=detail == "대출예약중",
                            requests=waitings,
                            requests_available=requests_available,
                        )
                else:
                    return HoldingStatus(
                        unavailable=UnavailableStatus(detail=detail),
                    )
        logger.warn("Cannot parse status")

    def parse_loan_status(
        self, root: Tag
    ) -> tuple[int | None, int | None, DateTime | None]:
        waitings = max_waitings = due = None
        if elem := root.select_one(".bookData .book_info.info04"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                if m := HOLDING_PATTERN.match(children[0].text):
                    waitings = int(m.group(1))
                    max_waitings = int(m.group(2))
            if len(children) >= 2:
                if m := DUE_PATTERN.match(children[1].text):
                    due = DateTime(
                        date=Date(
                            year=int(m.group(1)),
                            month=int(m.group(2)),
                            day=int(m.group(3)),
                        )
                    )
        return waitings, max_waitings, due


TITLE_PATTERN = re.compile(r"\d+\.\s*(.*)")
ISBN_PATTERN = re.compile(
    r"fnCollectionBookList\(\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*'(\d+)'\)"
)
STATUS_PATTERN = re.compile(r"(\w+)\s*(\([\w\d\s]+\))?")
HOLDING_PATTERN = re.compile(r"예약\s*\:\s*(\d+)명?\s*\/\s*(\d+)명")
DUE_PATTERN = re.compile(r"반납예정일[\s\:]*(\d{4})\.(\d{2})\.(\d{2})")
URL_PATTERN = re.compile(
    r"(?:fnSearchResultDetail|fnDetail)\("
    r"'?(\d+)'?"
    r"\s*,\s*"
    r"'?(\d+)'?"
    r"\s*,\s*"
    r"(?:"
    r"\'?\d+\'?"
    r"\s*,\s*"
    r")?"
    r"\'([\w\d]+)\'"
    r"\)"
)
