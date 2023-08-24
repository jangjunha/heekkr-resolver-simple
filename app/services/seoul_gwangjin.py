from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from app.services.common.jnet import JnetSearcher


__all__ = ("SeoulGwangjinService",)


class Searcher(JnetSearcher):
    @property
    def id_prefix(self) -> str:
        return "seoul-gwangjin:"

    @property
    def url_base(self) -> str:
        return "https://www.gwangjinlib.seoul.kr/"

    @property
    def path_search_index(self) -> str:
        return "/gjinfo/menu/10036/program/30010/plusSearchSimple.do"

    @property
    def path_search(self) -> str:
        return "/gjinfo/menu/10036/program/30010/plusSearchResultList.do"

    @property
    def path_export_text(self) -> str:
        return "/search/exportTextBookList.do"

    @property
    def path_book_detail(self) -> str:
        return "/gjinfo/menu/10036/program/30010/plusSearchDetailView.do"

    def transform_library_name_for_search(self, name: str) -> str:
        return f"서울시 광진구 {name}"


@register_service("seoul-gwangjin")
class SeoulGwangjinService(Service):
    def __init__(self) -> None:
        self.searcher = Searcher()

    async def get_libraries(self) -> Iterable[Library]:
        return await self.searcher.get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return self.searcher.search(keyword, library_ids)
