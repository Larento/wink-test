import asyncio
import re
from functools import lru_cache
from typing import Annotated, Any, Callable, Coroutine

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from pydantic import HttpUrl

from wink_test.balancer import calculate_should_redirect_to_cdn
from wink_test.dependencies import SettingsDependency


class Counter:
    def __init__(self):
        self.value = 0
        self.lock = asyncio.Lock()

    async def get(self):
        async with self.lock:
            return self.value

    async def increment(self):
        async with self.lock:
            self.value += 1

    async def reset(self):
        async with self.lock:
            self.value = 0


request_counter = Counter()


@lru_cache
def get_request_counter():
    return request_counter


class BalancerAPIRoute(APIRoute):
    @staticmethod
    def is_missing_query_param_error(error: Any) -> bool:
        """
        Возвращает `True`, если ошибка валидации запроса произошла из-за отсутствия query параметра. В других случаях возвращает `False`.
        """

        if isinstance(error, dict):
            try:
                error_type: Any = error["type"]
                error_loc: Any = error["loc"][0]
                return error_type == "missing" and error_loc == "query"
            except KeyError:
                return False
        else:
            return False

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except RequestValidationError as exc:
                print(exc)
                for error in exc.errors():
                    if self.is_missing_query_param_error(error):
                        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
                return await request_validation_exception_handler(request, exc)

        return custom_route_handler


router = APIRouter(route_class=BalancerAPIRoute)


@router.get("/")
async def balancer_root(
    video: HttpUrl,
    request_counter: Annotated[Counter, Depends(get_request_counter)],
    settings: SettingsDependency,
):
    if not settings:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    assert settings.cdn_host.host
    assert video.host

    redirect_url = video
    request_index = await request_counter.get()
    should_redirect_to_cdn = await calculate_should_redirect_to_cdn(request_index, settings.redirect_ratio)

    if should_redirect_to_cdn:
        # Поиск поддомена s1, s2, ..., sN.
        if match := re.search(r"^(s\d+)\.", video.host):
            file_server_subdomain = match.group(1)
            redirect_url = HttpUrl(
                f"{settings.cdn_host.scheme}://{settings.cdn_host.host}/{file_server_subdomain}{video.path}"
            )

    await request_counter.increment()
    return Response(
        headers={"location": str(redirect_url)},
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    )
