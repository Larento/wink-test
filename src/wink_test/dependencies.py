from functools import lru_cache

from pydantic import ValidationError

from wink_test.settings import Settings

__all__ = ("get_settings",)


@lru_cache
def get_settings():
    try:
        return Settings()  # type: ignore
    except ValidationError:
        return None
