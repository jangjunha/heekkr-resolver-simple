import dataclasses
import contextlib
import os

from aiohttp import ClientSession


@dataclasses.dataclass
class Address:
    x: float
    y: float


class Kakao(contextlib.AsyncContextDecorator):
    def __init__(self) -> None:
        key = os.environ.get("KAKAO_API_KEY")

        self.session = ClientSession(headers={"Authorization": f"KakaoAK {key}"})

    async def search_address(self, query: str) -> Address | None:
        async with self.session.get(
            "https://dapi.kakao.com/v2/local/search/address.json",
            params={
                "query": query,
                "analyze_type": "similar",
                "page": 1,
                "size": 1,
            },
        ) as response:
            res = await response.json()

        if res["meta"]["total_count"] < 1:
            return

        doc = res["documents"][0]
        return Address(
            x=float(doc["x"]),
            y=float(doc["y"]),
        )

    async def search_keyword(self, keyword: str) -> Address | None:
        async with self.session.get(
            "https://dapi.kakao.com/v2/local/search/keyword.json",
            params={
                "query": keyword,
                "size": 1,
            },
        ) as response:
            res = await response.json()

        if res["meta"]["total_count"] < 1:
            return

        doc = res["documents"][0]
        return Address(
            x=float(doc["x"]),
            y=float(doc["y"]),
        )

    async def __aenter__(self) -> "Kakao":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.session.close()
