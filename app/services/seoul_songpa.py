from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet_splib import JnetSplibSearcher


__all__ = ("SeoulSongpaService",)


class Searcher(JnetSplibSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-songpa:"

    @property
    def url_base(self) -> str:
        return "https://splib.or.kr/"

    @property
    def path_search_index(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultList.do"

    @property
    def path_export_excel(self) -> str:
        return "/book/exportExcelBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/intro/menu/10003/program/30001/plusSearchResultDetail.do"


@register_service("seoul-songpa")
class SeoulSongpaService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
