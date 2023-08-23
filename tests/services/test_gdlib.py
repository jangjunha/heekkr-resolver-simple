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
from app.services.gdlib import Searcher as BaseSearcher


class Searcher(BaseSearcher):
    async def get_libraries_response(self) -> str:
        with open(urllib.parse.urljoin(__file__, "gdlib_index.html"), "r") as f:
            return f.read()

    async def search_response(self, *args, **kwargs) -> str:
        with open(urllib.parse.urljoin(__file__, "gdlib_result.html"), "r") as f:
            return f.read()

    async def export_to_text_response(self, *args, **kwargs):
        assert False, "Must not be called"


@pytest.mark.asyncio
async def test_gdlib_get_libraries():
    searcher = Searcher()
    res = await searcher.get_libraries()
    assert res == [
        Library(id="gdlib:MA", name="성내도서관"),
        Library(id="gdlib:BR", name="해공도서관"),
        Library(id="gdlib:MB", name="강일도서관"),
        Library(id="gdlib:MC", name="암사도서관"),
        Library(id="gdlib:MD", name="천호도서관"),
        Library(id="gdlib:ME", name="둔촌도서관"),
        Library(id="gdlib:LH", name="가람슬기작은도서관"),
        Library(id="gdlib:LN", name="게냇골작은도서관"),
        Library(id="gdlib:LF", name="글고운작은도서관"),
        Library(id="gdlib:LS", name="글마루작은도서관"),
        Library(id="gdlib:LO", name="글익는작은도서관"),
        Library(id="gdlib:LG", name="글향기작은도서관"),
        Library(id="gdlib:LL", name="늘솔길작은도서관"),
        Library(id="gdlib:LI", name="반딧불작은도서관"),
        Library(id="gdlib:LT", name="부엉이작은도서관"),
        Library(id="gdlib:LQ", name="서원마을작은도서관"),
        Library(id="gdlib:LB", name="솔향기북카페"),
        Library(id="gdlib:LU", name="아람작은도서관"),
        Library(id="gdlib:LD", name="안말작은도서관"),
        Library(id="gdlib:LC", name="채우리작은도서관"),
        Library(id="gdlib:LE", name="책꾸러미작은도서관"),
        Library(id="gdlib:LA", name="작은도서관 웃는책"),
        Library(id="gdlib:LR", name="파랑새작은도서관"),
        Library(id="gdlib:LJ", name="해오름작은도서관"),
        Library(id="gdlib:LK", name="햇살작은도서관"),
        Library(id="gdlib:LX", name="다독다독 길동사거리점"),
        Library(id="gdlib:LY", name="다독다독 고분다리시장점"),
        Library(id="gdlib:LZ", name="다독다독 고덕점"),
        Library(id="gdlib:SA", name="다독다독 암사종합시장점"),
        Library(id="gdlib:SB", name="다독다독 굽은다리역점"),
        Library(id="gdlib:SC", name="다독다독 강일점"),
    ]


@pytest.mark.asyncio
async def test_gdlib_search():
    searcher = Searcher()
    res = [entity async for entity in searcher.search("", [])]
    assert res == [
        SearchEntity(
            book=Book(
                isbn="9791192579887",
                title="바다가 들리는 편의점. 2",
                author="마치다 소노코 지음 ; 황국영 옮김",
                publisher="모모",
                publish_date=PublishDate(year=2023),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="833.6-마86ㅂ-2",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="대출예약중"),
                        is_requested=True,
                        requests=2,
                        requests_available=True,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=100176713250&bookKey=100176713252&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788952793423",
                title="매일 갑니다, 편의점 : 어쩌다 편의점 인간이 된 남자의 생활 밀착 에세이",
                author="봉달호 지음",
                publisher="시공사",
                publish_date=PublishDate(year=2018),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="818-봉22ㅁ",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=113104847&bookKey=113104849&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791164160112",
                title="편의점에 간 멍청한 경제학자",
                author="고석균 지음",
                publisher="책들의정원",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="321.89-고54ㅍ",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=115024553&bookKey=115024555&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788963192642",
                title="수상한 편의점",
                author="박현숙 글 ; 장서영 그림",
                publisher="북멘토",
                publish_date=PublishDate(year=2018),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="C 808.9-북34ㅂ-28",
                    library_id="gdlib:BR",
                    location="해공어린이자료실",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            detail="",
                            due=DateTime(date=Date(year=2023, month=9, day=6)),
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=True,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=110918027&bookKey=110918029&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791170440048",
                title="외계인 편의점",
                author="박선화 글 ; 이경국 그림",
                publisher="소원나무",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="C 808.9-소66ㅅ-04",
                    library_id="gdlib:BR",
                    location="해공어린이자료실",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            detail="",
                            due=DateTime(date=Date(year=2023, month=9, day=3)),
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=True,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=117200700&bookKey=117200702&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788963194318",
                title="궁금한 편의점",
                author="박현숙 글 ; 홍찬주 그림",
                publisher="북멘토",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="C 813.8-박94교",
                    library_id="gdlib:BR",
                    location="해공어린이자료실",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=100138511257&bookKey=100138511260&publishFormCode=BO",
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
                    call_number="833.6-마86ㅂ",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            detail="",
                            due=DateTime(date=Date(year=2023, month=9, day=1)),
                        ),
                        is_requested=True,
                        requests=5,
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=100168789351&bookKey=100168789353&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571331",
                title="불편한 편의점 : 김호연 장편소설 : 큰글자도서",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="LP 813.7-김95ㅂ",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            detail="",
                            due=DateTime(date=Date(year=2023, month=9, day=4)),
                        ),
                        is_requested=True,
                        requests=1,
                        requests_available=True,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=100154332764&bookKey=100154332766&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791195793464",
                title="일본 편의점 매력을 보다 = 日本のコンビニその魅力を探る",
                author="김진태, 기은영, 이윤지 [공]지음",
                publisher="brainLEO",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="326.176-김78ㅇ",
                    library_id="gdlib:BR",
                    location="해공종합자료실",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=115107367&bookKey=115107369&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788936451585",
                title="편의점 비밀 요원 : 박주혜 동화",
                author="박주혜 지음 ; 정인하 그림",
                publisher="창비",
                publish_date=PublishDate(year=2020),
            ),
            holding_summaries=[
                HoldingSummary(
                    call_number="C 813.8-창48ㅅ-58",
                    library_id="gdlib:BR",
                    location="해공어린이자료실",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        requests_available=False,
                    ),
                )
            ],
            url="https://gdlibrary.or.kr/web/menu/10045/program/30003/searchResultDetail.do?recKey=100123988702&bookKey=100123988704&publishFormCode=BO",
        ),
    ]
