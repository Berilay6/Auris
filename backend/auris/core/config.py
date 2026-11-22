"""Uygulama yapılandırması.

Değerler ortam değişkenlerinden okunur (pydantic-settings):
    AURIS_DATA_DIR      - veri dizini (varsayılan: ./data)
    AURIS_CONFIG_DIR    - yapılandırma dizini (varsayılan: ./config)
    CELERY_BROKER_URL   - Celery broker adresi (varsayılan: redis://localhost:6379/0)
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    AURIS_DATA_DIR: Path = Path("data")
    AURIS_CONFIG_DIR: Path = Path("config")
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
