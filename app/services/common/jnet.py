import abc
import logging
import re
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
    @abc.abstractmethod
    def path_export(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def path_book_detail(self) -> str:
        ...

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
    async def get_libraries(self) -> list[Library]:
        text = await self.get_libraries_response()
        soup = BeautifulSoup(text, "lxml")
        res = []
        async with Kakao() as kakao:
            for li in soup.select("ul.searchCheckList li:not(.total)"):
                name = self.normalize_library_name(li.text.strip())
                if input := li.select_one("input[name='searchLibraryArr']"):
                    key = input.attrs["value"]
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
        return MultiDict(
            [
                ("searchType", "SIMPLE"),
                ("searchKey", "ALL"),
                ("searchKeyword", keyword),
                *(("searchLibraryArr", key) for key in library_keys),
            ]
        )

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
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        text = await self.search_response(keyword, library_ids)
        soup = BeautifulSoup(text, "lxml")
        results = soup.select("#contents ul.resultList > li:not(.emptyNote)")
        if len(results) == 0:
            return

        # Case #1
        if btn_area := soup.select_one(".resultHead"):
            if "목록저장" in btn_area.text:
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
                                        "status": self.parse_loan_status(li),
                                    },
                                },
                            }
                        )
                if books:
                    async for entity in self.export_to_text(books):
                        yield entity
                    return

        # Fallback
        for li in results:
            isbn = self.parse_isbn(li)
            library, location = await self.parse_site(li)
            yield SearchEntity(
                book=Book(
                    isbn=isbn,
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
                        status=self.parse_loan_status(li),
                    )
                ],
                url=self.parse_url(li),
            )

    async def export_to_text_response(self, infos: Iterable[dict]) -> str:
        async with ClientSession(self.url_base) as session, session.post(
            self.path_export,
            data=MultiDict(("check", info["id"]) for info in infos),
        ) as response:
            return await response.text()

    async def export_to_text(
        self,
        infos: Iterable[dict],
    ) -> AsyncIterable[SearchEntity]:
        text = await self.export_to_text_response(infos)

        header_text, *data = text.splitlines()
        header = header_text.split("\t")

        def find_index(*candidates: Iterable[str]) -> int:
            for c in candidates:
                if c in header:
                    return header.index(c)
            raise NotImplementedError(f"Cannot find {candidates=}")

        i_title = find_index("서명")
        i_author = find_index("저자")
        i_publisher = find_index("출판사", "발행자")
        i_publish_year = find_index("출판년도", "출판연도", "발행년도", "발행연도")
        i_call_number = find_index("청구기호")
        i_isbn = find_index("ISBN", "표준번호(ISBN, ISSN)")
        i_library = find_index("도서관")
        i_location = find_index("자료실")

        for line, info in zip(data, infos):
            parts = line.split("\t")

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

    def parse_title(self, root: Tag) -> str | None:
        if elem := root.select_one(".tit > a"):
            return elem.text.strip()
        logger.warn("Cannot parse title")

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

    def parse_author(self, root: Tag) -> str | None:
        if elem := root.select_one(".author > span:nth-child(1)"):
            return elem.text.removeprefix("저자 : ")
        logger.warn("Cannot parse author")

    def parse_publisher(self, root: Tag) -> str | None:
        if elem := root.select_one(".author > span:nth-child(2)"):
            return elem.text.removeprefix("발행자: ")
        logger.warn("Cannot parse publisher")

    def parse_publish_date(self, root: Tag) -> PublishDate | None:
        if elem := root.select_one(".author > span:nth-child(3)"):
            year_text = elem.text.removeprefix("발행연도: ")
            try:
                year = int(year_text)
            except ValueError:
                logger.warn("Cannot parse publish year text")
                return
            return PublishDate(year=year)
        logger.warn("Cannot parse publish date")

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

    def parse_loan_status(self, root: Tag) -> HoldingStatus | None:
        if bar := root.select_one(".bookStateBar"):
            if bar_txt := bar.select_one("p.txt"):
                if b := bar_txt.select_one("b"):
                    status_text = b.text.strip()
                else:
                    return

                if m := REQUESTS_PATTERN.search(bar_txt.text):
                    requests = int(m.group(1))
                else:
                    requests = None

                if m := DUE_PATTERN.search(bar_txt.text):
                    year = int(m.group(1))
                    month = int(m.group(2))
                    day = int(m.group(3))
                    due = DateTime(date=Date(year=year, month=month, day=day))
                else:
                    due = None
            else:
                logging.warn("Cannot parse loan status - bar_txt")
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
        logging.warn("Cannot parse loan status")


REQUESTS_PATTERN = re.compile(r"예약[\:\s]*(\d+)명")
DUE_PATTERN = re.compile(r"반납예정일[\:\s]*(\d{4})\.(\d{2})\.(\d{2})")
URL_PATTERN = re.compile(
    r"fnSearchResultDetail\((\d+)\s*,\s*(\d+)\s*,\s*\'([\w\d]+)\'\)"
)