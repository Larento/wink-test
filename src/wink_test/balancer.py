import math
from contextlib import asynccontextmanager
from fractions import Fraction
from typing import Annotated, Any, Callable

from asyncpg import Record
from asyncpg.pool import PoolConnectionProxy
from pydantic import BaseModel, BeforeValidator, HttpUrl, PositiveInt, TypeAdapter, UrlConstraints, field_serializer

from wink_test.postgres import Postgres

__all__ = (
    "BalancerSettings",
    "parse_redirect_ratio",
    "calculate_should_redirect_to_cdn",
    "BalancerSettingsDbModel",
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
                    "Переданное значение не соответствует требуемому формату: <кол-во редиректов на CDN>:<кол-во редиректов на origin сервера>"
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

    @field_serializer("redirect_ratio")
    def serialize_redirect_ratio(self, redirect_ratio: Fraction) -> str:
        """
        Сериализует отношение количества редиректов в строку.
        """
        return f"{redirect_ratio.numerator}:{redirect_ratio.denominator}"


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


class BalancerSettingsDbModel:
    table_name = "settings"

    def __init__(self, db_connection: Postgres, *, on_invalidate: Callable[[BalancerSettings], None] | None = None):
        self.db_connection = db_connection
        self.on_invalidate = on_invalidate

    @asynccontextmanager
    async def acquire_connection(self):
        assert self.db_connection.pool
        async with self.db_connection.pool.acquire() as conn:
            yield conn

    async def create_table(self):
        async with self.acquire_connection() as conn:
            await conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name}(
                    onerow_id bool PRIMARY KEY DEFAULT true,
                    cdn_host text,
                    redirect_ratio text,
                    CONSTRAINT onerow_uni CHECK (onerow_id)
                );
            """)

    async def create_object(self, settings: BalancerSettings) -> BalancerSettings:
        async with self.acquire_connection() as conn:
            dumped_settings = settings.model_dump(mode="json")
            await conn.execute(
                f"INSERT INTO {self.table_name}(cdn_host, redirect_ratio) VALUES($1, $2);",
                dumped_settings["cdn_host"],
                dumped_settings["redirect_ratio"],
            )

            if new_persistent_settings := await self._get_object(conn):
                if callable(self.on_invalidate):
                    self.on_invalidate(new_persistent_settings)
                return new_persistent_settings
            else:
                raise ValueError

    async def get_object(self) -> BalancerSettings | None:
        async with self.acquire_connection() as conn:
            return await self._get_object(conn)

    async def _get_object(self, connection: "PoolConnectionProxy[Record]") -> BalancerSettings | None:
        record = await connection.fetchrow(f"SELECT * FROM {self.table_name} WHERE onerow_id = true;")
        if record:
            return BalancerSettings(
                cdn_host=HttpUrl(record["cdn_host"]),
                redirect_ratio=parse_redirect_ratio(record["redirect_ratio"]),
            )

    async def update_object(self, settings: BalancerSettings) -> BalancerSettings | None:
        async with self.acquire_connection() as conn:
            dumped_settings = settings.model_dump(mode="json")
            await conn.execute(
                f"UPDATE {self.table_name} set cdn_host = $1, redirect_ratio = $2 WHERE onerow_id = true;",
                dumped_settings["cdn_host"],
                dumped_settings["redirect_ratio"],
            )

            if updated_settings := await self._get_object(conn):
                if callable(self.on_invalidate):
                    self.on_invalidate(updated_settings)
                return updated_settings
