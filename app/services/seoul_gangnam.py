from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulGangnamService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-gangnam:"

    @property
    def url_base(self) -> str:
        return "https://library.gangnam.go.kr/"

    @property
    def path_search_index(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultList.do"

    @property
    def path_export(self) -> str:
        return "/kolaseek/search/exportTextBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultDetail.do"

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 강남구 {name}"


@register_service("seoul-gangnam")
class SeoulGangnamService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
