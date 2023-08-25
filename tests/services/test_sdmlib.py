import urllib.parse

import pytest
from heekkr.book_pb2 import Book, PublishDate
from heekkr.common_pb2 import DateTime, Date
from heekkr.holding_pb2 import (
    HoldingSummary,
    UnavailableStatus,
    AvailableStatus,
    OnLoanStatus,
    HoldingStatus,
)
from heekkr.resolver_pb2 import SearchEntity

from app.core import Library
from app.services.seoul_seodaemun import Searcher as BaseSearcher


class Searcher(BaseSearcher):
    async def get_libraries_response(self) -> str:
        with open(urllib.parse.urljoin(__file__, "sdmlib_index.html"), "r") as f:
            return f.read()

    async def search_response(self, *args, **kwargs) -> str:
        with open(urllib.parse.urljoin(__file__, "sdmlib_result.html"), "r") as f:
            return f.read()


@pytest.mark.asyncio
async def test_sdmlib_get_libraries():
    searcher = Searcher()
    res = await searcher.get_libraries()
    assert res == [
        Library(
            id="seoul-seodaemun:MA",
            name="서대문구립이진아기념도서관",
        ),
        Library(
            id="seoul-seodaemun:MB",
            name="새롬어린이도서관",
        ),
        Library(
            id="seoul-seodaemun:MC",
            name="홍은도담도서관",
        ),
        Library(
            id="seoul-seodaemun:SA",
            name="알음알음작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SB",
            name="하늘샘작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SC",
            name="북아현 마을북카페",
        ),
        Library(
            id="seoul-seodaemun:SM",
            name="늘푸른 열린 작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SE",
            name="아이누리작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SK",
            name="파랑새작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SN",
            name="가슴따뜻한 작은 도서관",
        ),
        Library(
            id="seoul-seodaemun:SR",
            name="이팝꽃향기작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SP",
            name="논골작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SF",
            name="새싹작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SJ",
            name="행복작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SG",
            name="꿈이있는도서관",
        ),
        Library(
            id="seoul-seodaemun:SH",
            name="문화촌작은도서관",
        ),
        Library(
            id="seoul-seodaemun:SI",
            name="햇살작은도서관",
        ),
        Library(
            id="seoul-seodaemun:MD",
            name="아현역스마트도서관",
        ),
        Library(
            id="seoul-seodaemun:ME",
            name="홍제역스마트도서관",
        ),
        Library(
            id="seoul-seodaemun:MF",
            name="독립문역스마트도서관",
        ),
        Library(
            id="seoul-seodaemun:SS",
            name="구청스마트도서관",
        ),
    ]


@pytest.mark.asyncio
async def test_sdmlib_search():
    searcher = Searcher()
    res = [entity async for entity in searcher.search("", [])]
    assert res == [
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점 : 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="디지털도서관(온라인)",
                    call_number="813.6-ㄱ989ㅂ",
                    status=HoldingStatus(unavailable=UnavailableStatus(detail="전자도서관")),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=417869985&speciesKey=417869983&isbn=9791161571188&pubFormCode=EB",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571195",
                title="불편한 편의점 김호연 장편소설 ",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="디지털도서관(온라인)",
                    call_number="813.6-ㄱ989ㅂ",
                    status=HoldingStatus(unavailable=UnavailableStatus(detail="전자도서관")),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=425147031&speciesKey=425147029&isbn=9791161571195&pubFormCode=EB",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571379",
                title="불편한 편의점 : 김호연 장편소설. 2",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ-2=2",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=6,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=424120770&speciesKey=424120767&isbn=9791161571379&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점 : 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=3,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=408478644&speciesKey=408478642&isbn=9791161571188&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점: 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=1,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=419161046&speciesKey=419161044&isbn=9791161571188&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571379",
                title="불편한 편의점 : 김호연 장편소설. 2",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ-2",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=4,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=424120623&speciesKey=424120621&isbn=9791161571379&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점 : 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ=3",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=3,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=422230176&speciesKey=422230174&isbn=9791161571188&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571379",
                title="불편한 편의점 : 김호연 장편소설. 2",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실Ⅰ(3층)",
                    call_number="813.6-ㄱ989ㅂ-2=3",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약중"),
                        is_requested=False,
                        requests=5,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=424545568&speciesKey=424545566&isbn=9791161571379&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571454",
                title="불편한 편의점: 김호연 장편소설: 큰글자도서. 2",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실(3층 신간도서 코너)",
                    call_number="큰글 813.6-ㄱ989ㅂ-2",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="상호대차중"),
                        is_requested=False,
                        requests=0,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=427774258&speciesKey=427774256&isbn=9791161571454&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571331",
                title="불편한 편의점: 김호연 장편소설: 큰글자도서. 1",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="본관_종합자료실(3층 신간도서 코너)",
                    call_number="큰글 813.6-ㄱ989ㅂ-1",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            due=DateTime(date=Date(year=2023, month=9, day=9))
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=427774255&speciesKey=427774253&isbn=9791161571331&pubFormCode=MO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점 : 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="디지털도서관(온라인)",
                    call_number="813.6-ㄱ989ㅂ",
                    status=HoldingStatus(unavailable=UnavailableStatus(detail="전자도서관")),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=408699026&speciesKey=408699024&isbn=9791161571188&pubFormCode=EB",
        ),
        SearchEntity(
            book=Book(
                isbn="9786161848859",
                title="ร้านไม่สะดวกซื้อของคุณทกโก",
                author="เขียน: คิมโฮย็อน; แปล: มินตรา อินทรารัตน์",
                publisher="Piccolo",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-seodaemun:MA",
                    location="다문화자료실",
                    call_number="THA 813.7-ㄱ989ㄹ",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=False,
                    ),
                )
            ],
            url="https://lib.sdm.or.kr/sdmlib/menu/10003/program/30001/searchResultDetail.do?bookKey=424939250&speciesKey=424939248&isbn=9786161848859&pubFormCode=MO",
        ),
    ]
