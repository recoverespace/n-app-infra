from datetime import timedelta
from functools import lru_cache

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from typing import List 
from pydantic import Field  


class Settings(BaseSettings):
    PG_USER: str = "postgres"
    PG_PASSWORD: str = "postgres"
    PG_HOST: str = "postgres"
    PG_PORT: int = 5432
    PG_SCHEMA: str = "backend"
    REDIS_DSN: RedisDsn
    PROJECT: str = "Recovered API"
    SECRET_KEY: str = "VERY_SECRET_KEY"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = int(timedelta(hours=1).total_seconds())
    REFRESH_TOKEN_EXPIRE_SECONDS: int = int(timedelta(days=30).total_seconds())

    ANDROID_SHA256_FINGERPRINTS: List[str] = Field(default_factory=list)
    APPLE_APP_ID: str = "QHVW647327.com.app.recoveredspace"

    CENTRIFUGE_SCHEMA: str = "http"
    CENTRIFUGE_WS_SCHEMA: str = "ws"
    CENTRIFUGE_HOST: str = "127.0.0.1:8010"
    CENTRIFUGE_INTERNAL_HOST: str = "centrifugo:8010"
    CENTRIFUGE_API_KEY: str = "f058bc3f-5c58-4953-bc55-9a7345e848e8"
    CENTRIFUGE_SECRET: str = "abd30447-2ab2-40fd-959d-4b2fb234e686"
    CENTRIFUGE_TOKEN_TTL: int = int(timedelta(hours=1).total_seconds())
    CENTRIFUGE_CHAT_NAMESPACE_TEMPLATE: str = "chat:messages#{}"

    ONESIGNAL_APP_ID: str = ""
    ONESIGNAL_API_KEY: str = ""
    ONESIGNAL_DEV_APP_ID: str = ""
    ONESIGNAL_DEV_API_KEY: str = ""

    STORYBLOK_TOKEN: str = ""
    STORYBLOK_MAPI_TOKEN: str = ""

    STRIPE_ACCOUNT_ID: str = ""
    STRIPE_API_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    GSPREAD_USERS_URL: str = ""
    FEEL2HEAL_USERS_URL: str = "https://docs.google.com/spreadsheets/d/1aYLF2TLxMaS9fKF8cUL1m47gRRX2CVogzFNMBiyBcwc"
    GSPREAD_SERVICE_ACCOUNT_FILE: str = ""
    GSPREAD_SERVICE_ACCOUNT_JSON: str = "{}"

    FIREBASE_CERTIFICATE: str = ""

    VERSION: str = "0.0.1"
    GIT_HASH: str = ""
    GIT_BRANCH: str = ""
    SERVICE_PREFIX: str = ""

    # Circle.so settings
    CIRCLE_ADMIN_API_KEY: str = ""
    CIRCLE_HEADLESS_API_KEY: str = ""
    CIRCLE_SPACE_ID: str = ""

    CHAT_URL: str = "https://aichat-dev-apim-t55fh.azure-api.net/api/flexible-rag"
    CHAT_OAUTH_CLIENT_ID: str = ""
    CHAT_OAUTH_CLIENT_SECRET: str = ""
    CHAT_OAUTH_TENANT_ID: str = ""
    CHAT_OAUTH_SCOPE: str = "api://rcv-chat-api/.default"
    CHAT_OAUTH_SUBSCRIPTION_KEY: str = ""
    CHAT_MAX_MESSAGE_HISTORY: int = 99999
    CHAT_MAX_FACT_HISTORY: int = 99999
    CHAT_RECENT_FACT_DAYS: int = 5

    # Safeguarding (Azure Content Safety) settings
    SAFEGUARDING_ENABLED: bool = False
    SAFEGUARDING_BASE_URL: str = "https://dev-tap-aitools-o5qo-apim.azure-api.net/ai"
    SAFEGUARDING_TENANT_ID: str = ""
    SAFEGUARDING_CLIENT_ID: str = ""
    SAFEGUARDING_CLIENT_SECRET: str = ""
    SAFEGUARDING_API_SCOPE: str = ""
    SAFEGUARDING_SUBSCRIPTION_KEY: str = ""
    SAFEGUARDING_THRESHOLD: int = 4

    REPORTING_API_KEY: str = "reporting_api_key"

    MONITORING_ENABLED: bool = True
    TENANT_REQUIRED: bool = False
    ANONYMOUS_ACCESS_ENABLED: bool = True


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
