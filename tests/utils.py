import os
from unittest import mock

__all__ = ("patch_environ",)


def patch_environ(**kwargs: str):
    """
    Декоратор для замены значений переменных окружения при выполнении теста.
    """
    return mock.patch.dict(os.environ, kwargs)
