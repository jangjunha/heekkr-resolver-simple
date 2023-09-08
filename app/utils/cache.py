import dataclasses
import datetime
import io
import logging
import pickle

from aiocache.base import BaseCache
from aiocache.serializers import PickleSerializer
from google.cloud.exceptions import NotFound
from google.cloud.storage import Client


logger = logging.getLogger(__name__)


@dataclasses.dataclass
class CacheEntity:
    value: str
    expires_at: datetime.datetime | None


class SimpleGcsBackend(BaseCache):
    def __init__(self, bucket_name, **kwargs):
        super().__init__(**kwargs)
        self.client = Client()
        self.bucket = self.client.get_bucket(bucket_name)
        logger.debug("SimpleGcsBackend initialized")

    async def _get_entity(self, key) -> CacheEntity | None:
        logger.debug("_get_entity")
        blob = self.bucket.blob(key)
        with io.BytesIO() as f:
            try:
                blob.download_to_file(f)
            except NotFound:
                return None
            f.seek(0)
            return pickle.load(f)

    async def _get(self, key, encoding="utf-8", _conn=None):
        logger.debug(f"_get {key}")
        if entity := await self._get_entity(key):
            if entity.expires_at and entity.expires_at <= datetime.datetime.utcnow():
                return None
            return entity.value
        else:
            return None

    async def _gets(self, key, encoding="utf-8", _conn=None):
        logger.debug("_gets")
        return await self.get(key, encoding, _conn)

    async def _multi_get(self, keys, encoding="utf-8", _conn=None):
        logger.debug("_multi_get")
        return [self._get(key, encoding, _conn) for key in keys]

    async def _set_entity(self, key, entity: CacheEntity):
        logger.debug("_set_entity")
        blob = self.bucket.blob(key)
        with io.BytesIO() as f:
            pickle.dump(entity, f)
            f.seek(0)
            blob.upload_from_file(f)
        return True

    async def _set(self, key, value, ttl=None, _cas_token=None, _conn=None):
        logger.debug(f"_set {key}")
        entity = CacheEntity(
            value=value,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
            if ttl
            else None,
        )
        return await self._set_entity(key, entity)

    async def _multi_set(self, pairs, ttl=None, _conn=None):
        logger.debug("_multi_set")
        for key, value in pairs:
            await self._set(key, value, ttl=ttl)
        return True

    async def _add(self, key, value, ttl=None, _conn=None):
        logger.debug("_add")
        if self._exists(key):
            raise ValueError(
                "Key {} already exists, use .set to update the value".format(key)
            )
        await self._set(key, value, ttl=ttl)
        return True

    async def _exists(self, key, _conn=None):
        logger.debug(f"_exists {key}")
        blob = self.bucket.blob(key)
        return blob.exists()

    async def _increment(self, key, delta, _conn=None):
        if entity := await self._get_entity(key):
            entity.value = int(entity.value) + delta
            await self._set_entity(key, entity)
            return entity.value
        else:
            await self._set(key, delta)
            return delta

    async def _expire(self, key, ttl, _conn=None):
        if entity := await self._get_entity(key):
            entity.expires_at = (
                datetime.datetime.utcnow() + datetime.timedelta(seconds=ttl)
                if ttl is not None
                else None
            )
            await self._set_entity(key, entity)
            return True
        return False

    async def _delete(self, key, _conn=None):
        blob = self.bucket.blob(key)
        try:
            blob.delete()
        except NotFound:
            return 0
        return 1


class GcsCache(SimpleGcsBackend):
    NAME = "gcs"

    def __init__(self, serializer=None, **kwargs):
        super().__init__(serializer=serializer or PickleSerializer(), **kwargs)

    @classmethod
    def parse_uri_path(cls, path):
        return {}
