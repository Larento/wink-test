from fractions import Fraction
from typing import Annotated, Any

from pydantic import BeforeValidator, HttpUrl, PositiveInt, TypeAdapter, UrlConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = (
    "parse_redirect_ratio",
    "Settings",
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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="balancer_")

    cdn_host: Annotated[HttpUrl, UrlConstraints(host_required=True)]
    """
    URL сервиса CDN.
    """

    redirect_ratio: Annotated[Fraction, BeforeValidator(parse_redirect_ratio)]
    """
    Отношение редиректов на CDN и origin сервера.
    """
