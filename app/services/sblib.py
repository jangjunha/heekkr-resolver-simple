from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity
from multidict import MultiDict

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SblibService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "sblib:"

    @property
    def url_base(self) -> str:
        return "https://www.sblib.seoul.kr/"

    @property
    def path_search_index(self) -> str:
        return "/library/menu/10012/program/30003/searchSimple.do"

    @property
    def path_search(self) -> str:
        return "/library/menu/10012/program/30003/searchResultList.do"

    @property
    def path_export(self) -> str:
        return "/searchApi/exportTextList.do"

    @property
    def path_book_detail(self) -> str:
        return "/library/menu/10012/program/30003/searchResultDetail.do"

    def normalize_library_name(self, name: str) -> str:
        return f"{name}도서관"

    def search_query(self, keyword: str, library_keys: Iterable[str]) -> MultiDict:
        return MultiDict(
            [
                ("query", keyword),
                ("categoryManageCode", ",".join(library_keys)),
            ]
        )


@register_service("sblib")
class SblibService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
