import math
from fractions import Fraction
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, HttpUrl, PositiveInt, RedisDsn, TypeAdapter, UrlConstraints

__all__ = (
    "BalancerSettings",
    "parse_redirect_ratio",
    "calculate_should_redirect_to_cdn",
)

positive_int_validator = TypeAdapter[PositiveInt](PositiveInt)
"""
Валидатор целых чисел больше нуля.
"""


def parse_redirect_ratio(value: Any) -> Fraction:
    """
    Получает отношение количества редиректов на CDN к количеству редиректов на origin сервера.
    """

    match value:
        case Fraction():
            return value
        case str():
            try:
                cdn_redirect_count, origin_servers_redirect_count = map(int, value.split(":"))
            except ValueError:
                raise ValueError(
                    "Переданное значение не соответствует требуемому формату:\n\
                      <кол-во редиректов на CDN>:<кол-во редиректов на origin сервера>"
                )
            positive_int_validator.validate_python(cdn_redirect_count)
            positive_int_validator.validate_python(origin_servers_redirect_count)
            return Fraction(cdn_redirect_count, origin_servers_redirect_count)
        case _:
            raise ValueError("Передаваемое значение должно быть строкой.")


class BalancerSettings(BaseModel):
    """
    Настройки балансировщика.
    """

    cdn_host: Annotated[HttpUrl, UrlConstraints(host_required=True)]
    """
    URL сервиса CDN.
    """

    redirect_ratio: Annotated[Fraction, BeforeValidator(parse_redirect_ratio)]
    """
    Отношение редиректов на CDN и origin сервера.
    """

    redis_url: RedisDsn
    """
    URL хранилища Redis. В Redis хранится счетчик обработанных запросов. 
    """


async def calculate_should_redirect_to_cdn(request_index: int, redirect_ratio: Fraction) -> bool:
    """
    Определяет, делать ли редирект на CDN. Возвращает `True`, если это так.

    Каждый N-ый запрос отправляется на origin сервер, все остальные будут перенаправлены на CDN.

    :param request_index: порядковый номер запроса (начиная с 0).
    :param redirect_ratio: отношение количества редиректов на CDN и на origin сервера.
    """

    requests_count_per_block = redirect_ratio.numerator + redirect_ratio.denominator
    cdn_requests_count = redirect_ratio.numerator
    origin_servers_requests_count = redirect_ratio.denominator
    relative_request_index = request_index % requests_count_per_block

    if cdn_requests_count >= origin_servers_requests_count:
        do_origin_server_request_at_every = math.floor(1 + cdn_requests_count / origin_servers_requests_count)
        return (relative_request_index + 1) % do_origin_server_request_at_every != 0
    else:
        do_cdn_request_at_every = math.floor(1 + origin_servers_requests_count / cdn_requests_count)
        return (relative_request_index + 1) % do_cdn_request_at_every == 0
