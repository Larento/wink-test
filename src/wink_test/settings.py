from pydantic import BaseModel, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from wink_test.balancer import BalancerSettings, BalancerSettingsDbModel
from wink_test.postgres import Postgres, PostgresSettings

__all__ = (
    "DatabaseOnlySettings",
    "Settings",
    "construct_settings_from_env",
    "construct_settings_from_env_and_db",
)


class DatabaseOnlySettings(BaseSettings):
    def __hash__(self):
        return super(BaseModel, self).__hash__()

    model_config = SettingsConfigDict(
        frozen=True,
        env_prefix="balancer_",
        env_nested_delimiter="_",
        env_nested_max_split=1,
    )

    database: PostgresSettings | None = None
    """
    Настройки базы данных Postgres для хранения настроек балансировщика.
    """


class Settings(BalancerSettings, DatabaseOnlySettings):
    """
    Настройки приложения.
    """

    redis_url: RedisDsn
    """
    URL хранилища Redis. В Redis хранится счетчик обработанных запросов.
    """


def construct_settings_from_env():
    """
    Создаёт настройки приложения из переменных окружения.
    """
    return Settings()  # type: ignore


async def construct_settings_from_env_and_db(db_settings: PostgresSettings):
    """
    Создаёт настройки приложения из переменных окружения и данных из БД. При этом должно быть установлено подключение к БД и должна существовать запись с настройками балансировщика.
    """

    db_connection = Postgres(db_settings)
    async with db_connection.connect():
        model = BalancerSettingsDbModel(db_connection)
        await model.create_table()
        balancer_settings = await model.get_object()
        if balancer_settings:
            return Settings(
                cdn_host=balancer_settings.cdn_host,
                redirect_ratio=balancer_settings.redirect_ratio,
                database=db_settings,  # type: ignore
            )
