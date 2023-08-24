import urllib.parse
from typing import Iterable

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
from app.services.seoul_songpa import Searcher as BaseSearcher
from .splib_export import values


class Searcher(BaseSearcher):
    async def get_libraries_response(self) -> str:
        with open(urllib.parse.urljoin(__file__, "splib_index.html"), "r") as f:
            return f.read()

    async def search_response(self, *args, **kwargs) -> str:
        with open(urllib.parse.urljoin(__file__, "splib_result.html"), "r") as f:
            return f.read()

    async def export_to_excel_response(
        self, infos: Iterable[dict]
    ) -> Iterable[Iterable] | None:
        return values


@pytest.mark.asyncio
async def test_splib_get_libraries():
    searcher = Searcher()
    res = await searcher.get_libraries()
    assert res == [
        Library(id="seoul-songpa:ME", name="송파글마루도서관"),
        Library(id="seoul-songpa:MA", name="송파어린이도서관"),
        Library(id="seoul-songpa:MH", name="송파위례도서관"),
        Library(id="seoul-songpa:MB", name="거마도서관"),
        Library(id="seoul-songpa:MF", name="돌마리도서관"),
        Library(id="seoul-songpa:BA", name="소나무언덕1호도서관"),
        Library(id="seoul-songpa:BB", name="소나무언덕2호도서관"),
        Library(id="seoul-songpa:BC", name="소나무언덕3호도서관"),
        Library(id="seoul-songpa:BD", name="소나무언덕4호도서관"),
        Library(id="seoul-songpa:MC", name="소나무언덕잠실본동도서관"),
        Library(id="seoul-songpa:MD", name="송파어린이영어도서관"),
        Library(id="seoul-songpa:MG", name="가락몰도서관"),
        Library(id="seoul-songpa:BE", name="송이골작은도서관"),
        Library(id="seoul-songpa:QA", name="송파스마트도서관(잠실나루역)"),
        Library(id="seoul-songpa:QB", name="송파스마트도서관(방이역)"),
        Library(id="seoul-songpa:QC", name="송파스마트도서관(마천역)"),
        Library(id="seoul-songpa:QD", name="송파스마트도서관(거여역)"),
        Library(id="seoul-songpa:QE", name="송파스마트도서관(장지역)"),
        Library(id="seoul-songpa:QF", name="송파스마트도서관(잠실2동주민센터)"),
    ]


@pytest.mark.asyncio
async def test_splib_search():
    searcher = Searcher()
    res = [entity async for entity in searcher.search("", [])]
    assert res == [
        SearchEntity(
            book=Book(
                isbn="9791190174718",
                title="편의점",
                author="유기농볼셰비키 외 지음",
                publisher="안전가옥",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="813.7-안74편",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=363083079&bookKey=363083081&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788959407941",
                title="#점장아님주의, 편의점 : 석류 에세이 : ENFJ의 4년 5개월 편의점 알바 이야기",
                author="석류 지음",
                publisher="시대의창",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="818-석296해",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=376198915&bookKey=376198917&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788996575832",
                title="마이 코리안 델리 : 백인 사위와 한국인 장모의 좌충우돌 편의점 운영기",
                author="벤 라이더 하우 지음 ; 이수영 옮김",
                publisher="정은문고",
                publish_date=PublishDate(year=2011),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="848-하66마",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=324412609&bookKey=324412611&publishFormCode=BO",
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
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="818-봉22매",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            due=DateTime(date=Date(year=2023, month=8, day=31))
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=347621369&bookKey=347621371&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788961558853",
                title="마이콜, 세상은 넓고 편의점은 많아",
                author="아기공룡 둘리 지음",
                publisher="톡",
                publish_date=PublishDate(year=2019),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="818-아18마",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=362333449&bookKey=362333451&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9788965965442",
                title="(지적인 현대인을 위한)지식 편의점. [3], 과학, 신을 꿈꾸는 인간 편",
                author="이시한 지음",
                publisher="흐름",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="001.3-이58지-3",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=377354490&bookKey=377354492&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791165795818",
                title="오늘도 지킵니다, 편의점 : 카운터 너머에서 배운 단짠단짠 인생의 맛",
                author="봉달호 글 ; 유총총 그림",
                publisher="시공사",
                publish_date=PublishDate(year=2021),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="818-봉22오",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            due=DateTime(date=Date(year=2023, month=8, day=30))
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=380706987&bookKey=380706989&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791161571355",
                title="큰글자도서 불편한 편의점  :  김호연 장편소설:김호연 장편소설",
                author="김호연 지음",
                publisher="나무옆의자",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층)",
                    call_number="큰글자 813.7-김95불",
                    status=HoldingStatus(
                        unavailable=UnavailableStatus(detail="대출예약중"),
                        is_requested=True,
                        requests=4,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=376412501&bookKey=376412503&publishFormCode=BO",
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
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지혜마루(2층북가든)",
                    call_number="813.7-범66우",
                    status=HoldingStatus(
                        available=AvailableStatus(detail="비치중"),
                        is_requested=False,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=372297753&bookKey=372297755&publishFormCode=BO",
        ),
        SearchEntity(
            book=Book(
                isbn="9791160808902",
                title="(한입에 쓱싹)편의점 과학 : 삼각김밥부터 계산대까지, 세상 모든 물건의 과학",
                author="이창욱 지음",
                publisher="곰곰",
                publish_date=PublishDate(year=2022),
            ),
            holding_summaries=[
                HoldingSummary(
                    library_id="seoul-songpa:ME",
                    location="송파글마루_지식마루(3층)",
                    call_number="404-이82편",
                    status=HoldingStatus(
                        on_loan=OnLoanStatus(
                            due=DateTime(date=Date(year=2023, month=8, day=8))
                        ),
                        is_requested=False,
                        requests=0,
                        requests_available=True,
                    ),
                )
            ],
            url="https://splib.or.kr/intro/menu/10003/program/30001/plusSearchResultDetail.do?recKey=375152694&bookKey=375152696&publishFormCode=BO",
        ),
    ]
