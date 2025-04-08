from pydantic_settings import BaseSettings, SettingsConfigDict

from wink_test.balancer import BalancerSettings
__all__ = ("Settings",)


class Settings(BalancerSettings, BaseSettings):
    """
    Настройки приложения.
    """

    model_config = SettingsConfigDict(env_prefix="balancer_", frozen=True)

    """
    Отношение редиректов на CDN и origin сервера.
    """
