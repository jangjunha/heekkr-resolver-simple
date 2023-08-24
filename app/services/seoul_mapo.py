from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulMapoService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-mapo:"

    @property
    def url_base(self) -> str:
        return "https://mplib.mapo.go.kr/"

    @property
    def path_search_index(self) -> str:
        return "/mcl/MENU1039/PGM3007/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/mcl/PGM3007/plusSearchResultList.do"

    @property
    def path_export_excel(self) -> str:
        return "/cmmn/exportExcelBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/mcl/MENU1039/PGM3007/plusSearchDetailView.do"

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 마포구 {name}"


@register_service("seoul-mapo")
class SeoulMapoService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
