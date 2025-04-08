import asyncio
import os
from unittest import mock

import aiohttp
import aiohttp.client_exceptions
import aiohttp.http_exceptions

__all__ = ("patch_environ", "get_random_video_url", "wait_for_balancer_api")


def patch_environ(**kwargs: str):
    """
    Декоратор для замены значений переменных окружения при выполнении теста.
    """
    return mock.patch.dict(os.environ, kwargs)


def get_random_video_url(video_id: int):
    """
    Генерирует URL видео-файла на origin сервере.

    :param video_id: ID видео.
    """
    return f"http://s1.origin-cluster/video/{video_id}/file.m3u8"


async def wait_for_balancer_api(client: aiohttp.ClientSession):
    """
    Ожидает доступности сервиса балансировщика.

    :param client: HTTP клиент сервиса.
    """

    for _ in range(5):
        try:
            response = await client.get("/health")
            if response.status == 200:
                return
        except aiohttp.client_exceptions.ClientError:
            await asyncio.sleep(0.5)
            continue
    raise TimeoutError
