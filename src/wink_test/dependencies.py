from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import ValidationError

from wink_test.settings import Settings

__all__ = (
    "get_settings",
    "SettingsDependency",
)


@lru_cache
def get_settings():
    try:
        return Settings()  # type: ignore
    except ValidationError:
        return None


SettingsDependency = Annotated[Settings | None, Depends(get_settings)]
