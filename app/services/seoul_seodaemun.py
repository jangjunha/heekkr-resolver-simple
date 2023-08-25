import logging
import re
from typing import AsyncIterable, Iterable
import urllib.parse

from bs4 import Tag
from heekkr.book_pb2 import PublishDate
from heekkr.common_pb2 import DateTime, Date
from heekkr.holding_pb2 import HoldingStatus
from heekkr.resolver_pb2 import SearchEntity
from multidict import MultiDict

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher
from app.utils.text import select_closest


__all__ = ("SeoulSeodaemunService",)

logger = logging.getLogger(__name__)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-seodaemun:"

    @property
    def url_base(self) -> str:
        return "https://lib.sdm.or.kr/"

    @property
    def path_search_index(self) -> str:
        return "/sdmlib/menu/10003/program/30001/searchSimple.do"

    @property
    def path_search(self) -> str:
        return "/sdmlib/menu/10003/program/30001/searchResultList.do"

    @property
    def path_book_detail(self) -> str:
        return "/sdmlib/menu/10003/program/30001/searchResultDetail.do"

    def _get_libraries_select_items(self, root: Tag) -> Iterable[Tag]:
        return root.select("#contents ol.finder_lib > li")

    def _get_libraries_select_input(self, item: Tag) -> Tag | None:
        return item.select_one("input[type=checkbox]")

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 서대문구 {name}"

    def search_select_results(self, root: Tag) -> list[Tag]:
        return root.select(
            "#contents .bookList > ul > "
            "li:not(.emptyNote):not(.noResultNote):not(.message)"
        )

    def search_query(self, keyword: str, library_keys: Iterable[str]) -> MultiDict:
        query = MultiDict(
            [
                ("searchType", "SIMPLE"),
                ("searchKey", "ALL"),
                ("searchKeyword", keyword),
                *(("searchManageCodeArr", key) for key in library_keys),
            ]
        )
        return query

    def parse_title(self, root: Tag) -> str | None:
        if elem := root.select_one(".book_name .kor a"):
            return elem.attrs["title"]
        logger.warning("Cannot parse title")

    def parse_author(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info01 .kor"):
            return elem.text.strip()
        logger.warning("Cannot parse author")

    def parse_publisher(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02 .kor"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                return children[0].text.strip()
        logger.warning("Cannot parse publisher")

    def parse_publish_date(self, root: Tag) -> PublishDate | None:
        if elem := root.select_one(".bookData .book_info.info02 .kor"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 2:
                year_str = children[1].text.strip()
                try:
                    year = int(year_str)
                except ValueError:
                    logger.warning("Cannot parse publish year to integer")
                    return
                return PublishDate(year=year)
        logger.warning("Cannot parse publish date")

    def parse_isbn(self, root: Tag) -> str:
        if m := self.parse_url_parts(root):
            _, _, isbn, _ = m
            return isbn
        raise RuntimeError("Canont parse ISBN")

    async def parse_site(self, root: Tag) -> tuple[Library, str | None]:
        for elem in root.select(".bookData .book_info.info03 > p.kor"):
            text = elem.text.strip()
            if m := RE_LIBRARY.search(text):
                library_name = m.group(1)
                location = m.group(2)
                libraries = list(await self.get_libraries())
                library = select_closest(
                    [(lib, lib.name) for lib in libraries], library_name
                )
                return library, location
        raise RuntimeError("Cannot parse library")

    def parse_call_number(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02 .kor"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 5:
                return children[4].text.strip()
        logger.warning("Cannot parse call number")

    def parse_loan_status_type_b(self, root: Tag) -> tuple[int | None, DateTime | None]:
        waitings = due = None
        for elem in root.select(".bookData .book_info.info03 .kor"):
            if m := self.REQUESTS_PATTERN.search(elem.text):
                waitings = int(m.group(1))
            if m := self.DUE_PATTERN.search(elem.text):
                due = DateTime(
                    date=Date(
                        year=int(m.group(1)),
                        month=int(m.group(2)),
                        day=int(m.group(3)),
                    )
                )
        return waitings, due

    def parse_holding_status(self, root: Tag) -> HoldingStatus | None:
        return self.parse_holding_status_type_b(root)

    def parse_url_parts(self, root: Tag) -> tuple[str, str, str, str] | None:
        for elem in root.select(".bookData a"):
            if m := self.URL_PATTERN.search(elem.attrs.get("onclick", "")):
                bookKey = m.group(1)
                speciesKey = m.group(2)
                isbn = m.group(3)
                pubFormCode = m.group(4)
                return bookKey, speciesKey, isbn, pubFormCode

    def parse_url(self, root: Tag) -> str | None:
        if m := self.parse_url_parts(root):
            bookKey, speciesKey, isbn, pubFormCode = m
            parts = list(
                urllib.parse.urlparse(
                    urllib.parse.urljoin(self.url_base, self.path_book_detail)
                )
            )
            parts[4] = urllib.parse.urlencode(
                {
                    "bookKey": bookKey,
                    "speciesKey": speciesKey,
                    "isbn": isbn,
                    "pubFormCode": pubFormCode,
                }
            )
            return urllib.parse.urlunparse(parts)

    URL_PATTERN = re.compile(
        r"fnDetail\("
        r"'?(\d+)'?"
        r"\s*,\s*"
        r"'?(\d+)'?"
        r"\s*,\s*"
        r"\'?(\d+)\'?"
        r"\s*,\s*"
        r"\'([\w\d]+)\'"
        r"\)"
    )


@register_service("seoul-seodaemun")
class SeoulSeodaemunService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)


RE_LIBRARY = re.compile(r"^\[([\w\s()]+)\]\s*([\w\s()]+)")
