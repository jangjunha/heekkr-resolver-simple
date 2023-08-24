from typing import AsyncIterable, Iterable

from bs4 import BeautifulSoup
from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service, Coordinate
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulGwanakService",)

from app.utils.kakao import Kakao


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-gwanak:"

    @property
    def url_base(self) -> str:
        return "https://lib.gwanak.go.kr/"

    @property
    def path_search_index(self) -> str:
        return "/galib/menu/10003/program/30001/searchSimple.do"

    @property
    def path_search(self) -> str:
        return "/galib/menu/10003/program/30001/searchResultList.do"

    @property
    def path_export_text(self) -> str:
        return "/kolaseek/search/exportTextBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/galib/menu/10003/program/30001/searchResultDetail.do"

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 관악구 {name}"

    async def _get_libraries(self) -> list[Library]:
        text = await self.get_libraries_response()
        soup = BeautifulSoup(text, "lxml")
        res = []
        async with Kakao() as kakao:
            for li in soup.select("ul.chk_lib li"):
                name = self.normalize_library_name(li.text.strip())
                if input := li.select_one("input[name='searchLibraryArr']"):
                    key = input.attrs["value"]
                    if key == "ALL":
                        continue
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


@register_service("seoul-gwanak")
class SeoulGwanakService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
