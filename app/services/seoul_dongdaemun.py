from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulDongdaemunService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-dongdaemun:"

    @property
    def url_base(self) -> str:
        return "https://www.l4d.or.kr/"

    @property
    def path_search_index(self) -> str:
        return "/intro/menu/10096/program/30010/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/intro/menu/10096/program/30010/plusSearchResultList.do"

    @property
    def path_export(self) -> str:
        return "/search/exportTextBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/intro/menu/10096/program/30010/plusSearchResultDetail.do"

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 동대문구 {name}"


@register_service("seoul-dongdaemun")
class SeoulDongdaemunService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
