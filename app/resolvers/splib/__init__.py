from typing import AsyncIterable

from heekkr.resolver_pb2 import (
    GetLibrariesRequest,
    GetLibrariesResponse,
    SearchRequest,
    SearchResponse,
)
from heekkr.resolver_pb2_grpc import ResolverServicer

from .searcher import get_libraries, search


class Resolver(ResolverServicer):
    async def GetLibraries(
        self, request: GetLibrariesRequest, context
    ) -> GetLibrariesResponse:
        return GetLibrariesResponse(libraries=await get_libraries())

    async def Search(
        self, request: SearchRequest, context
    ) -> AsyncIterable[SearchResponse]:
        yield SearchResponse(
            entities=[e async for e in search(request.term, request.library_ids)]
        )
