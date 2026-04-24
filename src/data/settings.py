from functools import lru_cache

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PG_USER: str
    PG_PASSWORD: str
    PG_HOST: str
    PG_PORT: int
    PG_SCHEMA: str
    REDIS_DSN: RedisDsn
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3600
    GCS_BUCKET: str = "local"
    EXTERNAL_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file="./.env", extra="ignore")

    @property
    def POSTGRES_DSN(self) -> PostgresDsn:
        return PostgresDsn(
            f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_SCHEMA}"
        )


@lru_cache
def get_settings():
    return Settings.model_validate({})


settings = get_settings()
