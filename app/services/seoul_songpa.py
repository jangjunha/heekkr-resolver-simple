import logging
import re
from typing import AsyncIterable, Iterable

from bs4 import Tag
from heekkr.book_pb2 import PublishDate
from heekkr.holding_pb2 import HoldingStatus
from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulSongpaService",)

from app.utils.text import select_closest

logger = logging.getLogger(__name__)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-songpa:"

    @property
    def url_base(self) -> str:
        return "https://splib.or.kr/"

    @property
    def path_search_index(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultList.do"

    @property
    def path_export_excel(self) -> str:
        return "/book/exportExcelBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultDetail.do"

    def _get_libraries_select_items(self, root: Tag) -> Iterable[Tag]:
        return root.select("#contents .searchCheckBox ul > li")

    def _get_libraries_select_input(self, item: Tag) -> Tag | None:
        return item.select_one("input[type=checkbox]")

    def search_select_results(self, root: Tag) -> list[Tag]:
        return root.select(
            "#contents .bookList > ul > "
            "li:not(.emptyNote):not(.noResultNote):not(.message)"
        )

    def parse_title(self, root: Tag) -> str | None:
        if elem := root.select_one(".book_name .title"):
            if m := self.TITLE_PATTERN.match(elem.text):
                return m.group(1)
        logger.warning("Cannot parse title")

    def parse_author(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info01"):
            return elem.text.strip()
        logger.warning("Cannot parse author")

    def parse_publisher(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                return children[0].text.strip()
        logger.warning("Cannot parse publisher")

    def parse_publish_date(self, root: Tag) -> PublishDate | None:
        if elem := root.select_one(".bookData .book_info.info02"):
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
        if a := root.select_one(".bookDetailInfo a.btn_haveinfo"):
            if m := self.ISBN_PATTERN.match(a.attrs["onclick"]):
                return m.group(1)
        raise RuntimeError("Canont parse ISBN")

    async def parse_site(self, root: Tag) -> tuple[Library, str | None]:
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
                logger.warning("Cannot parse location")
            return library, location
        raise RuntimeError("Cannot parse library")

    def parse_call_number(self, root: Tag) -> str | None:
        if elem := root.select_one(".bookData .book_info.info02"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 3:
                return children[2].text.strip()
        logger.warning("Cannot parse call number")

    def parse_holding_status(self, root: Tag) -> HoldingStatus | None:
        return self.parse_holding_status_type_b(root)

    TITLE_PATTERN = re.compile(r"\d+\.\s*(.*)")
    ISBN_PATTERN = re.compile(
        r"fnCollectionBookList\(\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*'(\d+)'\)"
    )
    URL_PATTERN = re.compile(
        r"fnSearchResultDetail\("
        r"'?(\d+)'?"
        r"\s*,\s*"
        r"'?(\d+)'?"
        r"\s*,\s*"
        r"\'([\w\d]+)\'"
        r"\)"
    )


@register_service("seoul-songpa")
class SeoulSongpaService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
