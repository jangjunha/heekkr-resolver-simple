import asyncio
import dataclasses
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
from heekkr.library_pb2 import Library
from heekkr.resolver_pb2 import SearchEntity
from multidict import MultiDict


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class LibraryConfig:
    search_key: str
    library: Library


@cached(ttl=60 * 60 * 24)
async def get_library_configs() -> list[LibraryConfig]:
    async with ClientSession() as session:
        async with session.get(
            "https://splib.or.kr/intro/menu/10022/contents/40003/contents.do"
        ) as response:
            text = await response.text()
        soup = BeautifulSoup(text, "lxml")

        root = soup.select_one("#contents .publiclib_wrap ul")
        if root is None:
            raise RuntimeError("Cannot parse libraries list")

        libs = []
        for li in root.find_all("li", recursive=False):
            title = li.find("h3")
            if m := re.match(r"[\w\s\d]+", title.text):
                name = m.group(0).strip()
            else:
                raise RuntimeError("Cannot parse library name")

            a = title.find("a")
            href = a.attrs["href"]
            if m := re.match(r"\/([\w\d]+)\/", href):
                key = m.group(1)
            else:
                raise RuntimeError("Cannot parse library key")

            libs.append((name, key, href))

        async def parse_library_index(name: str, key: str, href: str) -> LibraryConfig:
            async with session.get(
                urllib.parse.urljoin("https://splib.or.kr/", href)
            ) as response:
                text = await response.text()
            soup = BeautifulSoup(text, "lxml")
            if lib_input := soup.select_one(
                "#mainSearchForm input[name=searchLibraryArr]"
            ):
                search_key = lib_input.attrs["value"]
                return LibraryConfig(search_key, Library(id=f"splib:{key}", name=name))
            else:
                raise RuntimeError("Cannot parse library search key")

        return await asyncio.gather(*(parse_library_index(*lib) for lib in libs))


async def get_libraries() -> Iterable[Library]:
    return (config.library for config in await get_library_configs())


async def search(keyword: str, libraries: Iterable[str]) -> AsyncIterable[SearchEntity]:
    library_keys = [
        lib.search_key
        for lib in await get_library_configs()
        if lib.library.id in libraries
    ]
    async with ClientSession() as session, session.post(
        "https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultList.do",
        data=MultiDict(
            [
                ("searchType", "SIMPLE"),
                ("searchCategory", "BOOK"),
                ("searchKey", "ALL"),
                ("searchKeyword", keyword),
                *(("searchLibraryArr", key) for key in library_keys),
            ]
        ),
    ) as response:
        text = await response.text()
    soup = BeautifulSoup(text, "lxml")

    root = soup.select_one("#searchForm .bookList .listWrap")
    if root is None:
        return
    for li in root.find_all("li", recursive=False):
        library, location = await parse_library(li)
        yield SearchEntity(
            book=Book(
                isbn=parse_isbn(li),
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
                    status=parse_status(li),
                )
            ],
        )


def parse_title(root: Tag) -> str | None:
    if elem := root.select_one(".book_name .title"):
        if m := TITLE_PATTERN.match(elem.text):
            return m.group(1)
    logger.warn("Cannot parse title")


def parse_isbn(root: Tag) -> str | None:
    if a := root.select_one(".bookDetailInfo a[title='소장정보 보기']"):
        if m := ISBN_PATTERN.match(a.attrs["onclick"]):
            return m.group(1)
    logger.warn("Cannot parse isbn")


def parse_author(root: Tag) -> str | None:
    if elem := root.select_one(".bookData .book_info.info01"):
        return elem.text.strip()
    logger.warn("Cannot parse author")


def parse_publisher(root: Tag) -> str | None:
    if elem := root.select_one(".bookData .book_info.info02"):
        children = elem.find_all("span", recursive=False)
        if len(children) >= 1:
            return children[0].text.strip()
    logger.warn("Cannot parse publisher")


def parse_publish_date(root: Tag) -> PublishDate | None:
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


async def parse_library(root: Tag) -> tuple[Library, str | None]:
    if elem := root.select_one(".bookData .book_info.info03"):
        children = elem.find_all("span", recursive=False)
        if len(children) >= 1:
            library_str = children[0].text.strip()
            library = next(
                lib for lib in await get_libraries() if lib.name == library_str
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


def parse_call_number(root: Tag) -> str | None:
    if elem := root.select_one(".bookData .book_info.info02"):
        children = elem.find_all("span", recursive=False)
        if len(children) >= 3:
            return children[2].text.strip()
    logger.warn("Cannot parse call number")


def parse_status(
    root: Tag,
) -> HoldingStatus | None:
    if elem := root.select_one(".bookData .status"):
        text = elem.text.strip()
        if m := STATUS_PATTERN.match(text):
            status_text = m.group(1)
            detail = m.group(2)
            if status_text == "대출가능":
                return HoldingStatus(available=AvailableStatus(detail=detail))
            if status_text == "대출불가":
                if detail == "대출중":
                    waitings, waiting_available, due = parse_loan_status(root)
                    return HoldingStatus(
                        on_loan=OnLoanStatus(due=due),
                        is_requested=waitings > 0 if waitings else False,
                        requests=waitings,
                        requests_available=waiting_available,
                    )
                else:
                    return HoldingStatus(
                        unavailable=UnavailableStatus(detail=detail),
                        is_requested=detail == "대출예약중",
                    )
    logger.warn("Cannot parse status")


def parse_loan_status(root: Tag) -> tuple[int | None, bool, DateTime | None]:
    waitings = due = None
    waiting_available = False
    if elem := root.select_one(".bookData .book_info.info04"):
        children = elem.find_all("span", recursive=False)
        if len(children) >= 1:
            if m := HOLDING_PATTERN.match(children[0]):
                waitings = int(m.group(1))
                max_waitings = int(m.group(2))
                waiting_available = waitings < max_waitings
        if len(children) >= 2:
            if m := DUE_PATTERN.match(children[1]):
                due = DateTime(
                    date=Date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                )
    return waitings, waiting_available, due


TITLE_PATTERN = re.compile(r"\d+\.\s*(.*)")
ISBN_PATTERN = re.compile(
    r"fnCollectionBookList\(\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*[\w']+\s*,\s*'(\d+)'\)"
)
STATUS_PATTERN = re.compile(r"(\w+)\s*(\([\w\d\s]+\))?")
HOLDING_PATTERN = re.compile(r"예약\s*\:\s*(\d+)명?\s*\/\s*(\d+)명")
DUE_PATTERN = re.compile(r"반납예정일[\s\:]*(\d{4})\.(\d{2})\.(\d{2})")
