from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from pydantic import ValidationError
from redis.asyncio import Redis

from wink_test.balancer import BalancerSettings, BalancerSettingsDbModel
from wink_test.postgres import Postgres
from wink_test.settings import (
    DatabaseOnlySettings,
    Settings,
    construct_settings_from_env,
    construct_settings_from_env_and_db,
)
from wink_test.shared_counter import SharedCounter

__all__ = (
    "AppState",
    "get_app_state",
    "get_settings",
    "SettingsDependency",
    "get_redis_connection",
    "RedisConnectionDependency",
    "get_request_counter",
    "RequestCounterDependency",
    "get_db_connection",
    "DbConnectionDependency",
    "get_balancer_settings_db_model",
    "BalancerSettingsDbModelDependency",
)


@dataclass
class AppState:
    settings: Settings | None = None
    redis_connection: Redis | None = None
    request_counter: SharedCounter | None = None
    db_connection: Postgres | None = None
    balancer_settings_db_model: BalancerSettingsDbModel | None = None

    def update_balancer_settings(self, new_settings: BalancerSettings):
        if current_settings := self.settings:
            self.settings = Settings(
                cdn_host=new_settings.cdn_host,
                redirect_ratio=new_settings.redirect_ratio,
                redis_url=current_settings.redis_url,
                database=current_settings.database,
            )


app_state = AppState()


def get_app_state():
    return app_state


async def get_settings():
    if not app_state.settings:
        try:
            if db_settings := DatabaseOnlySettings().database:
                app_state.settings = await construct_settings_from_env_and_db(db_settings)
        except ValidationError:
            pass

        try:
            app_state.settings = construct_settings_from_env()
        except ValidationError:
            pass

    if app_state.settings:
        return app_state.settings
    else:
        raise SystemError("Сервису не были предоставлены необходимые настройки, дальнейшая работа невозможна.")


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def get_redis_connection(settings: SettingsDependency):
    if not app_state.redis_connection:
        assert settings.redis_url.host
        assert settings.redis_url.port
        app_state.redis_connection = Redis(host=settings.redis_url.host, port=settings.redis_url.port)

    return app_state.redis_connection


RedisConnectionDependency = Annotated[Redis, Depends(get_redis_connection)]


def get_request_counter(redis_connection: RedisConnectionDependency):
    if not app_state.request_counter:
        app_state.request_counter = SharedCounter(redis_connection, "request-counter")

    return app_state.request_counter


RequestCounterDependency = Annotated[SharedCounter, Depends(get_request_counter)]


def get_db_connection(settings: SettingsDependency):
    if not app_state.db_connection and settings.database:
        app_state.db_connection = Postgres(settings=settings.database)

    return app_state.db_connection


DbConnectionDependency = Annotated[Postgres | None, Depends(get_db_connection)]


def get_balancer_settings_db_model(db_connection: DbConnectionDependency):
    def invalidate(new_settings: BalancerSettings):
        app_state.update_balancer_settings(new_settings)

    if not app_state.balancer_settings_db_model and db_connection:
        app_state.balancer_settings_db_model = BalancerSettingsDbModel(db_connection, on_invalidate=invalidate)

    return app_state.balancer_settings_db_model


BalancerSettingsDbModelDependency = Annotated[BalancerSettingsDbModel | None, Depends(get_balancer_settings_db_model)]
