import dataclasses
import contextlib
import logging
import os

from aiohttp import ClientSession


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Address:
    x: float
    y: float


class Kakao(contextlib.AsyncContextDecorator):
    def __init__(self) -> None:
        key = os.environ.get("KAKAO_API_KEY")

        self.session = (
            ClientSession(headers={"Authorization": f"KakaoAK {key}"}) if key else None
        )

    async def search_address(self, query: str) -> Address | None:
        if not self.session:
            return None

        logger.debug(f"search_address {query}")
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

            if response.status != 200:
                logger.error(
                    f"Request failed with {response.status}",
                    extra={"response": response, "body": res},
                )
                return

        if res["meta"]["total_count"] < 1:
            return

        doc = res["documents"][0]
        return Address(
            x=float(doc["x"]),
            y=float(doc["y"]),
        )

    async def search_keyword(self, keyword: str) -> Address | None:
        if not self.session:
            return None

        logger.debug(f"search_keyword {keyword}")
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
        if self.session:
            await self.session.close()
