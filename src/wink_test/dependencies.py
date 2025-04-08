from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import ValidationError
from redis.asyncio import Redis

from wink_test.settings import Settings
from wink_test.shared_counter import SharedCounter

__all__ = (
    "get_settings",
    "SettingsDependency",
    "get_redis_connection",
    "RedisConnectionDependency",
    "get_request_counter",
    "RequestCounterDependency",
)


@lru_cache
def get_settings():
    try:
        return Settings()  # type: ignore
    except ValidationError:
        return None


SettingsDependency = Annotated[Settings | None, Depends(get_settings)]


@lru_cache
def get_redis_connection(settings: SettingsDependency):
    if settings:
        assert settings.redis_url.host
        assert settings.redis_url.port
        return Redis(host=settings.redis_url.host, port=settings.redis_url.port)
    else:
        return None


RedisConnectionDependency = Annotated[Redis | None, Depends(get_redis_connection)]


@lru_cache
def get_request_counter(redis_connection: RedisConnectionDependency):
    if redis_connection:
        return SharedCounter(redis_connection, "request-counter")
    else:
        return None


RequestCounterDependency = Annotated[SharedCounter | None, Depends(get_request_counter)]
