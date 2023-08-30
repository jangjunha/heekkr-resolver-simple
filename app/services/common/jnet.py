import abc
import logging
import re
from io import BytesIO
from typing import AsyncIterable, Iterable
import urllib.parse

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


class JnetSearcher(metaclass=abc.ABCMeta):
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
    def path_export_text(self) -> str:
        raise NotImplementedError()

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
            _ = self.path_export_text
            return True
        except NotImplementedError:
            pass
        try:
            _ = self.path_export_excel
            return True
        except NotImplementedError:
            pass
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

    def _get_libraries_select_items(self, root: Tag) -> Iterable[Tag]:
        return root.select("ul.searchCheckList li:not(.total)")

    def _get_libraries_select_input(self, item: Tag) -> Tag | None:
        return item.select_one("input[name='searchLibraryArr']")

    async def _get_libraries(self) -> list[Library]:
        text = await self.get_libraries_response()
        soup = BeautifulSoup(text, "lxml")
        res = []
        async with Kakao() as kakao:
            for li in self._get_libraries_select_items(soup):
                name = self.normalize_library_name(li.text.strip())
                if input := self._get_libraries_select_input(li):
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

    @cached(ttl=60 * 60 * 24, alias="default")
    async def get_libraries(self) -> list[Library]:
        return await self._get_libraries()

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

    def search_select_results(self, root: Tag) -> list[Tag]:
        return root.select(
            "#contents ul.resultList > "
            "li:not(.emptyNote):not(.noResultNote):not(.message)"
        )

    async def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        text = await self.search_response(keyword, library_ids)
        soup = BeautifulSoup(text, "lxml")
        results = self.search_select_results(soup)
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
                                    "status": self.parse_holding_status(
                                        li
                                    ),  # TODO: check parse_status
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
            library, location = await self.parse_site(li)
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
                        status=self.parse_holding_status(li),
                    )
                ],
                url=self.parse_url(li),
            )

    async def export_to_text_response(self, infos: Iterable[dict]) -> str | None:
        try:
            path = self.path_export_text
        except NotImplementedError:
            return None
        async with ClientSession(self.url_base) as session, session.post(
            path,
            data=MultiDict(("check", info["id"]) for info in infos),
        ) as response:
            if response.ok:
                return await response.text()

    async def export_to_excel_response(self, infos: Iterable[dict]) -> str | None:
        try:
            path = self.path_export_excel
        except NotImplementedError:
            return None
        async with ClientSession(self.url_base) as session, session.get(
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
        header = None
        if text := await self.export_to_text_response(infos):
            header_text, *data_texts = text.splitlines()
            header = header_text.split("\t")
            data = [line.split("\t") for line in data_texts]

        if header is None:
            if res := await self.export_to_excel_response(infos):
                header, *data = res

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
        i_location = find_index("자료실")

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

    def parse_id(self, root: Tag) -> str | None:
        if elem := root.select_one("input[name='check']"):
            return elem.attrs["value"]
        elif parts := (self.parse_id_from_url(root)):
            return "^".join(parts)

    def parse_id_from_url(self, root: Tag) -> tuple[str, str, str] | None:
        for elem in root.select("a"):
            if m := self.URL_PATTERN.search(elem.attrs["onclick"]):
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
        if elem := root.select_one(".tit > a"):
            return elem.text.strip()
        logger.warning("Cannot parse title")

    def parse_author(self, root: Tag) -> str | None:
        if elem := root.select_one(".author > span:nth-child(1)"):
            return elem.text.removeprefix("저자 : ")
        logger.warning("Cannot parse author")

    def parse_publisher(self, root: Tag) -> str | None:
        if elem := root.select_one(".author > span:nth-child(2)"):
            return elem.text.removeprefix("발행자: ")
        logger.warning("Cannot parse publisher")

    def parse_publish_date(self, root: Tag) -> PublishDate | None:
        if elem := root.select_one(".author > span:nth-child(3)"):
            year_text = elem.text.removeprefix("발행연도: ")
            try:
                year = int(year_text)
            except ValueError:
                logger.warning("Cannot parse publish year text")
                return
            return PublishDate(year=year)
        logger.warning("Cannot parse publish date")

    def parse_isbn(self, root: Tag) -> str:
        for sp in root.select(".data > span"):
            text = sp.text.strip()
            if text.startswith("ISBN:"):
                return text.removeprefix("ISBN:").strip()
        raise RuntimeError("Canont parse ISBN")

    def parse_call_number(self, root: Tag) -> str | None:
        for sp in root.select(".data > span"):
            text = "".join(sp.find_all(string=True, recursive=False)).strip()
            if text.startswith("청구기호:"):
                return text.removeprefix("청구기호:").strip()
        logger.warning("Canont parse call number")

    async def parse_site(self, root: Tag) -> tuple[Library, str | None]:
        library_text = location_text = None
        for sp in root.select(".site > span"):
            text = sp.text.strip()
            if text.startswith("도서관:"):
                library_text = text.removeprefix("도서관:").strip()
            elif text.startswith("자료실:"):
                location_text = text.removeprefix("자료실:").strip()
        if not library_text:
            raise RuntimeError("Cannot find library")
        library = select_closest(
            [(lib, lib.name) for lib in await self.get_libraries()], library_text
        )
        return library, location_text

    def parse_holding_status(self, root: Tag) -> HoldingStatus | None:
        if bar := root.select_one(".bookStateBar"):
            if bar_txt := bar.select_one("p.txt"):
                if b := bar_txt.select_one("b"):
                    status_text = b.text.strip()
                else:
                    return

                if m := self.REQUESTS_PATTERN.search(bar_txt.text):
                    requests = int(m.group(1))
                else:
                    requests = None

                if m := self.DUE_PATTERN.search(bar_txt.text):
                    year = int(m.group(1))
                    month = int(m.group(2))
                    day = int(m.group(3))
                    due = DateTime(date=Date(year=year, month=month, day=day))
                else:
                    due = None
            else:
                logger.warning("Cannot parse loan status - bar_txt")
                return

            if request_btn := bar.select_one(".stateArea .state.typeA"):
                waiting_available = request_btn.text.strip() == "도서예약신청"
            else:
                waiting_available = False

            if status_text.startswith("대출가능"):
                return HoldingStatus(
                    available=AvailableStatus(
                        detail=status_text.removeprefix("대출가능").strip("[]()"),
                    ),
                    requests_available=waiting_available,
                )
            if status_text.startswith("대출불가"):
                detail = status_text.removeprefix("대출불가").strip("[]()")
                if "대출중" in detail:
                    return HoldingStatus(
                        on_loan=OnLoanStatus(
                            detail=detail.removeprefix("대출중").strip("[]()"),
                            due=due,
                        ),
                        is_requested=(
                            (requests > 0 if requests else False)
                            if requests is not None
                            else None
                        ),
                        requests=requests,
                        requests_available=waiting_available,
                    )
                else:
                    return HoldingStatus(
                        unavailable=UnavailableStatus(detail=detail),
                        is_requested="예약" in detail,
                        requests=requests,
                        requests_available=waiting_available,
                    )
        logger.warning("Cannot parse loan status")

    def parse_requests_available_type_b(self, root: Tag) -> bool:
        for elem in root.select(".bookBtnWrap a"):
            if onclick := elem.attrs.get("onclick"):
                if "fnLoanReservationApplyProc" in onclick:
                    return True
        return False

    def parse_loan_status_type_b(self, root: Tag) -> tuple[int | None, DateTime | None]:
        waitings = due = None
        if elem := root.select_one(".bookData .book_info.info04"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                if m := self.REQUESTS_PATTERN.search(children[0].text):
                    waitings = int(m.group(1))
            if len(children) >= 2:
                if m := self.DUE_PATTERN.search(children[1].text):
                    due = DateTime(
                        date=Date(
                            year=int(m.group(1)),
                            month=int(m.group(2)),
                            day=int(m.group(3)),
                        )
                    )
        return waitings, due

    def parse_holding_status_type_b(self, root: Tag) -> HoldingStatus | None:
        if elem := root.select_one(".bookData .status"):
            text = elem.text.strip()
            if m := self.STATUS_PATTERN_TYPE_B.search(text):
                status_text = m.group(1)
                detail = m.group(2).strip("[]()")
                requests_available = self.parse_requests_available_type_b(root)
                waitings, due = self.parse_loan_status_type_b(root)
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
        logger.warning("Cannot parse status")

    def __repr__(self):
        cls = self.__class__
        return f"{cls.__module__}.{cls.__name__}"

    REQUESTS_PATTERN = re.compile(r"예약[\:\s]*(\d+)명?\s*(?:\/\s*(\d+)명?)?")
    DUE_PATTERN = re.compile(r"반납예정일[\:\s]*(\d{4})\.(\d{2})\.(\d{2})")
    URL_PATTERN = re.compile(
        r"(?:fnSearchResultDetail|fnSearchDetailView)\("
        r"(\d+)"
        r"\s*,\s*"
        r"(\d+)"
        r"\s*,\s*"
        r"\'([\w\d]+)\'"
        r"\)"
    )
    STATUS_PATTERN_TYPE_B = re.compile(r"(\w+)\s*(\([\w\d\s]+\))?")
