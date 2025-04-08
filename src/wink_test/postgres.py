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

    database_name: str
    """
    Название БД.
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
                database=self.settings.database_name,
            ) as pool:
                self.pool = pool
                yield
        finally:
            self.pool = None
