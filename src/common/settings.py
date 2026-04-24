from functools import lru_cache

from pydantic import RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    TESTING: int = 0
    EXTERNAL_URL: str = "http://localhost:8000"
    REDIS_DSN: RedisDsn
    GCS_BUCKET: str = "local"
    MONITORING_ENABLED: bool = True
    model_config = SettingsConfigDict(env_file="./.env", extra="ignore")


@lru_cache
def get_settings():
    return Settings.model_validate({})


settings = get_settings()
