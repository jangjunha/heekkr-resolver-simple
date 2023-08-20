from typing import AsyncIterable, Iterable

from heekkr.resolver_pb2 import SearchEntity

from app.core import Library, Service, register_service
from .searcher import get_libraries, search


@register_service("splib")
class SplibService(Service):
    async def get_libraries(self) -> Iterable[Library]:
        return await get_libraries()

    def search(
        self, keyword: str, library_ids: Iterable[str]
    ) -> AsyncIterable[SearchEntity]:
        return search(keyword, library_ids)
