import logging
import re
from typing import AsyncIterable, Iterable

from bs4 import Tag
from heekkr.book_pb2 import PublishDate
from heekkr.common_pb2 import DateTime, Date
from heekkr.holding_pb2 import (
    HoldingStatus,
    AvailableStatus,
    OnLoanStatus,
    UnavailableStatus,
)
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

    def parse_requests_available(self, root: Tag) -> bool:
        for elem in root.select(".bookBtnWrap a"):
            if onclick := elem.attrs.get("onclick"):
                if "fnLoanReservationApplyProc" in onclick:
                    return True
        return False

    def parse_loan_status(
        self, root: Tag
    ) -> tuple[int | None, int | None, DateTime | None]:
        waitings = max_waitings = due = None
        if elem := root.select_one(".bookData .book_info.info04"):
            children = elem.find_all("span", recursive=False)
            if len(children) >= 1:
                if m := self.REQUESTS_PATTERN.match(children[0].text):
                    waitings = int(m.group(1))
                    max_waitings = int(m.group(2))
            if len(children) >= 2:
                if m := self.DUE_PATTERN.match(children[1].text):
                    due = DateTime(
                        date=Date(
                            year=int(m.group(1)),
                            month=int(m.group(2)),
                            day=int(m.group(3)),
                        )
                    )
        return waitings, max_waitings, due

    def parse_holding_status(
        self,
        root: Tag,
    ) -> HoldingStatus | None:
        if elem := root.select_one(".bookData .status"):
            text = elem.text.strip()
            if m := self.STATUS_PATTERN.search(text):
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
        logger.warning("Cannot parse status")

    TITLE_PATTERN = re.compile(r"\d+\.\s*(.*)")
    ISBN_PATTERN = re.compile(
        r"fnCollectionBookList\(\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*'(\d+)'\)"
    )
    STATUS_PATTERN = re.compile(r"(\w+)\s*(\([\w\d\s]+\))?")
    REQUESTS_PATTERN = re.compile(r"예약\s*\:\s*(\d+)명?\s*\/\s*(\d+)명")
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
