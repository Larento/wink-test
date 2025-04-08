from contextlib import asynccontextmanager

import asyncpg
from pydantic import BaseModel, PostgresDsn

__all__ = ("Postgres",)


class PostgresSettings(BaseModel):
    """
    Модель настроек базы данных Postgresql.
    """

    url: PostgresDsn
    """
    URL базы данных Postgresql.
    """

    user: str
    """
    Имя пользователя БД.
    """

    password: str
    """
    Пароль пользователя БД.
    """

    name: str
    """
    Название используемой БД.
    """


class Postgres:
    """
    Класс, оборачивающий соединение с БД.
    """

    def __init__(self, settings: PostgresSettings):
        self.settings = settings
        self.pool: asyncpg.Pool[asyncpg.Record] | None = None

    @asynccontextmanager
    async def connect(self):
        try:
            async with asyncpg.create_pool(
                dsn=str(self.settings.url),
                user=self.settings.user,
                password=self.settings.password,
                database=self.settings.name,
            ) as pool:
                self.pool = pool
                yield
        finally:
            self.pool = None
