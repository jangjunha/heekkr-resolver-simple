import urllib.parse

import pytest
from heekkr.book_pb2 import Book, PublishDate
from heekkr.holding_pb2 import (
    HoldingSummary,
    UnavailableStatus,
    AvailableStatus,
    HoldingStatus,
)
from heekkr.resolver_pb2 import SearchEntity

from app.core import Library
from app.services.sblib import Searcher as BaseSearcher


class Searcher(BaseSearcher):
    async def get_libraries_response(self) -> str:
        with open(urllib.parse.urljoin(__file__, "sblib_index.html"), "r") as f:
            return f.read()

    async def search_response(self, *args, **kwargs) -> str:
        with open(urllib.parse.urljoin(__file__, "sblib_result.html"), "r") as f:
            return f.read()

    async def export_to_text_response(self, *args, **kwargs):
        with open(urllib.parse.urljoin(__file__, "sblib_export.txt"), "r") as f:
            return f.read()


@pytest.mark.asyncio
async def test_sblib_get_libraries():
    searcher = Searcher()
    res = await searcher.get_libraries()
    assert res == [
        Library(id="sblib:BR", name="성북정보도서관", coordinate=None),
        Library(id="sblib:MA", name="아리랑도서관", coordinate=None),
        Library(id="sblib:BT", name="해오름도서관", coordinate=None),
        Library(id="sblib:TR", name="새날도서관", coordinate=None),
        Library(id="sblib:ME", name="꿈마루도서관", coordinate=None),
        Library(id="sblib:MF", name="미리내도서관", coordinate=None),
        Library(id="sblib:MI", name="달빛마루도서관", coordinate=None),
        Library(id="sblib:MG", name="정릉도서관", coordinate=None),
        Library(id="sblib:MJ", name="청수도서관", coordinate=None),
        Library(id="sblib:MK", name="월곡꿈그림도서관", coordinate=None),
        Library(id="sblib:ML", name="아리랑어린이도서관", coordinate=None),
        Library(id="sblib:MX", name="성북이음도서관", coordinate=None),
        Library(id="sblib:MM", name="장위행복누림도서관", coordinate=None),
        Library(id="sblib:MN", name="성북길빛도서관", coordinate=None),
        Library(id="sblib:MO", name="글빛도서관", coordinate=None),
        Library(id="sblib:MZ", name="오동숲속도서관", coordinate=None),
    ]


@pytest.mark.asyncio
async def test_sblib_search():
    searcher = Searcher()
    res = [entity async for entity in searcher.search("", [])]
    assert res == [
        SearchEntity(
            book=Book(
                isbn="9788952235268",
                title="편의점 인간",
                author="무라타 사야카 지음 ; 김석희 옮김",
                publisher="살림",
                publish_date=PublishDate(year=2016),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="833.6-무292ㅍ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약 2명"),
                        is_requested=True,
                        requests=2,
                        requests_available=True,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9791169090704",
                title="편의점 재영씨",
                author="신재영 지음",
                publisher="에쎄",
                publish_date=PublishDate(year=2023),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="818-신73ㅍ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="상호대차"),
                        is_requested=False,
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9788937488825",
                title="편의점 사회학",
                author="지은이: 전상인",
                publisher="민음사",
                publish_date=PublishDate(year=2014),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="304-전52ㅍ",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치자료"),
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9788963192642",
                title="수상한 편의점",
                author="박현숙 글 ; 장서영 그림",
                publisher="북멘토",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]어린이자료실",
                    call_number="813.8-북34ㅅ-[v.6]",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치자료"),
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571379",
                title="불편한 편의점. 2",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="813.7-김95ㅂ-v.2",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약 3명"),
                        is_requested=True,
                        requests=3,
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9791192579504",
                title="바다가 들리는 편의점",
                author="마치다 소노코 지음 ; 황국영 옮김",
                publisher="모모",
                publish_date=PublishDate(year=2023),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="833.6-마86ㅂ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약 3명"),
                        is_requested=True,
                        requests=3,
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9788964964477",
                title="우리만의 편의점 레시피",
                author="범유진 지음",
                publisher="탐",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="813.7-범66ㅇ",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치자료"),
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9784167911300",
                title="コンビニ人間 = 편의점 인간",
                author="村田沙耶香 著",
                publisher="文藝春秋",
                publish_date=PublishDate(year=2020),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]다문화자료실",
                    call_number="JPN 833.6-무292ㅋ",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치자료"),
                        requests_available=False,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9791158363178",
                title="두근두근 편의점  : 김영진 그림책",
                author="김영진 지음",
                publisher="책읽는곰",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]유아자료실",
                    call_number="유 808-김64ㄷ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="상호대차"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571188",
                title="불편한 편의점  : 김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="sblib:BR",
                    location="[성북]종합자료실",
                    call_number="813.7-김95ㅂ",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="예약 3명"),
                        is_requested=True,
                        requests=3,
                        requests_available=False,
                    ),
                )
            ],
        ),
    ]
