import asyncio
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import aiohttp
import aiohttp.client_exceptions
import aiohttp.http_exceptions

__all__ = ("patch_environ", "get_random_video_url", "wait_for_balancer_api", "external_services")


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


external_services_compose_file_path = Path(__file__).parent.parent / "docker-compose.external-services.yaml"

external_services_compose_up_cmd: list[str] = [
    "docker",
    "compose",
    "-f ",
    str(external_services_compose_file_path),
    "up",
    "-d",
]

external_services_compose_down_cmd: list[str] = [
    "docker",
    "-f ",
    str(external_services_compose_file_path),
    "down",
]


@contextmanager
def external_services():
    """
    Менеджер контекста для запуска внешних сервисов (Redis) через Docker Compose.
    """

    try:
        process = subprocess.run(
            " ".join(external_services_compose_up_cmd),
            stdout=subprocess.DEVNULL,
            shell=True,
        )
        process.check_returncode()
        yield
    finally:
        subprocess.run(
            " ".join(external_services_compose_down_cmd),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=True,
        )
