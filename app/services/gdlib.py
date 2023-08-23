from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("GdlibService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "gdlib:"

    @property
    def url_base(self) -> str:
        return "https://gdlibrary.or.kr/"

    @property
    def path_search_index(self) -> str:
        return "/web/menu/10045/program/30003/searchSimple.do"

    @property
    def path_search(self) -> str:
        return "/web/menu/10045/program/30003/searchResultList.do"

    @property
    def path_export(self) -> str:
        raise NotImplementedError()

    @property
    def path_book_detail(self) -> str:
        return "/web/menu/10045/program/30003/searchResultDetail.do"

    def normalize_library_name(self, name: str) -> str:
        return name.replace("북카페:", "다독다독 ")


@register_service("gdlib")
class GdlibService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
