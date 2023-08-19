import logging
import re
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
from heekkr.library_pb2 import Library
from heekkr.resolver_pb2 import SearchEntity
from multidict import MultiDict


ID_PREFIX = "gdlib:"
logger = logging.getLogger(__name__)


@cached(ttl=60 * 60 * 24)
async def get_libraries() -> list[Library]:
    async with ClientSession() as session, session.get(
        "https://gdlibrary.or.kr/web/menu/10045/program/30003/searchSimple.do"
    ) as response:
        text = await response.text()
    soup = BeautifulSoup(text, "lxml")
    res = []
    for li in soup.select("#searchForm ul.searchCheckList li:not(.total)"):
        name = li.text.strip()
        if input := li.select_one("input[name='searchLibraryArr']"):
            key = input.attrs["value"]
            res.append(Library(id=f"{ID_PREFIX}{key}", name=name))
    return res


async def search(
    keyword: str, library_ids: Iterable[str]
) -> AsyncIterable[SearchEntity]:
    async with ClientSession() as session, session.post(
        "https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultList.do",
        data=MultiDict(
            [
                ("searchType", "SIMPLE"),
                ("searchSort", "RANK"),
                ("searchkey", "ALL"),
                ("searchKeyword", keyword),
                *(
                    ("searchLibraryArr", lid.removeprefix(ID_PREFIX))
                    for lid in library_ids
                ),
            ]
        ),
    ) as response:
        text = await response.text()
    soup = BeautifulSoup(text, "lxml")

    for li in soup.select("#contents ul.resultList > li:not(.emptyNote)"):
        isbn = parse_isbn(li)
        library, location = await parse_site(li)
        yield SearchEntity(
            book=Book(
                isbn=isbn,
                title=parse_title(li),
                author=parse_author(li),
                publisher=parse_publisher(li),
                publish_date=parse_publish_date(li),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id=library.id,
                    location=location,
                    call_number=parse_call_number(li),
                    status=parse_loan_status(li),
                )
            ],
        )


def parse_title(root: Tag) -> str | None:
    if elem := root.select_one(".tit > a"):
        return elem.text.strip()
    logger.warn("Cannot parse title")


def parse_author(root: Tag) -> str | None:
    if elem := root.select_one(".author > span:nth-child(1)"):
        return elem.text.removeprefix("저자 : ")
    logger.warn("Cannot parse author")


def parse_publisher(root: Tag) -> str | None:
    if elem := root.select_one(".author > span:nth-child(2)"):
        return elem.text.removeprefix("발행자: ")
    logger.warn("Cannot parse publisher")


def parse_publish_date(root: Tag) -> PublishDate | None:
    if elem := root.select_one(".author > span:nth-child(3)"):
        year_text = elem.text.removeprefix("발행연도: ")
        try:
            year = int(year_text)
        except ValueError:
            logger.warn("Cannot parse publish year text")
            return
        return PublishDate(year=year)
    logger.warn("Cannot parse publish date")


def parse_isbn(root: Tag) -> str:
    for sp in root.select(".data > span"):
        text = sp.text.strip()
        if text.startswith("ISBN:"):
            return text.removeprefix("ISBN:").strip()
    raise RuntimeError("Canont parse ISBN")


def parse_call_number(root: Tag) -> str | None:
    for sp in root.select(".data > span"):
        text = "".join(sp.find_all(text=True, recursive=False)).strip()
        if text.startswith("청구기호:"):
            return text.removeprefix("청구기호:").strip()
    logger.warning("Canont parse call number")


async def parse_site(root: Tag) -> tuple[Library, str | None]:
    library_text = location_text = None
    for sp in root.select(".site > span"):
        text = sp.text.strip()
        if text.startswith("도서관:"):
            library_text = text.removeprefix("도서관:").strip()
        elif text.startswith("자료실:"):
            location_text = text.removeprefix("자료실:").strip()
    library = next(lib for lib in await get_libraries() if lib.name == library_text)
    return library, location_text


def parse_loan_status(root: Tag) -> HoldingStatus | None:
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
                    detail=status_text.removeprefix("대출가능").strip("[]"),
                )
            )
        if status_text.startswith("대출불가"):
            detail = status_text.removeprefix("대출불가").strip("[]")
            if detail == "대출중":
                return HoldingStatus(
                    on_loan=OnLoanStatus(
                        due=due,
                    ),
                    is_requested=requests > 0 if requests else False,
                    requests=requests,
                    requests_available=waiting_available,
                )
            else:
                return HoldingStatus(
                    unavailable=UnavailableStatus(detail=detail),
                    is_requested=detail == "대출예약중",
                )
    logging.warn("Cannot parse loan status")


REQUESTS_PATTERN = re.compile(r"\(예약[\:\s]*(\d+)명\)")
DUE_PATTERN = re.compile(r"\(반납예정일[\:\s]*(\d{4})\.(\d{2})\.(\d{2})\)")
