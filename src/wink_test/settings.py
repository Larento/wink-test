from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from wink_test.balancer import BalancerSettings
__all__ = ("Settings",)


class Settings(BalancerSettings, BaseSettings):
    """
    Настройки приложения.
    """

    model_config = SettingsConfigDict(env_prefix="balancer_", frozen=True)

    redis_url: RedisDsn
    """
    URL хранилища Redis. В Redis хранится счетчик обработанных запросов. 
    """
    Отношение редиректов на CDN и origin сервера.
    """
