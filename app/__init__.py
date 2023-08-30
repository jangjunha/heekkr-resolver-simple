# ruff: noqa: E402

import asyncio
import os
from typing import AsyncIterable

from aiocache import caches
from aiostream import stream


def resolve_cache_config():
    if bucket_name := os.environ.get("GCS_CACHE_BUCKET", None):
        return {
            "cache": "app.utils.cache.GcsCache",
            "bucket_name": bucket_name,
        }
    else:
        return {"cache": "aiocache.SimpleMemoryCache"}


caches.set_config({"default": resolve_cache_config()})


from heekkr.common_pb2 import LatLng
from heekkr.resolver_pb2 import (
    GetLibrariesRequest,
    GetLibrariesResponse,
    SearchRequest,
    SearchResponse,
)
from heekkr.library_pb2 import Library
from heekkr.resolver_pb2_grpc import ResolverServicer

from .core import Library as ServiceLibrary, services


class Resolver(ResolverServicer):
    async def GetLibraries(
        self, request: GetLibrariesRequest, context
    ) -> GetLibrariesResponse:
        return GetLibrariesResponse(
            libraries=[
                convert_library(library)
                for libraries in await asyncio.gather(
                    *(service.get_libraries() for _, service in services.items())
                )
                for library in libraries
            ]
        )

    async def Search(
        self, request: SearchRequest, context
    ) -> AsyncIterable[SearchResponse]:
        library_ids = set(request.library_ids or ())
        service_ids = set(library_id.split(":")[0] for library_id in library_ids)

        async with stream.merge(
            *(
                service.search(
                    request.term,
                    {
                        library_id
                        for library_id in library_ids
                        if library_id.startswith(f"{name}:")
                    },
                )
                for name, service in services.items()
                if name in service_ids
            )
        ).stream() as streamer:
            async for entity in streamer:
                yield SearchResponse(entities=[entity])


def convert_library(lib: ServiceLibrary) -> Library:
    return Library(
        id=lib.id,
        name=lib.name,
        resolver_id="simple",
        coordinate=(
            LatLng(latitude=lib.coordinate.latitude, longitude=lib.coordinate.longitude)
            if lib.coordinate
            else None
        ),
    )
