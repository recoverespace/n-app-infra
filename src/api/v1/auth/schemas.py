from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, field_validator


class TokenModel(BaseModel):
    access_token: str
    refresh_token: str | None
    access_token_expires_in: int | None
    refresh_token_expires_in: int | None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None
    expires_in: int | None = None


class FirebaseTokenModel(BaseModel):
    token: str


class RefreshTokenModel(BaseModel):
    refresh_token: str


class RefreshAccessTokenRequestModel(BaseModel):
    refresh_token: str


class TokenResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    access_token_expires_in: int | None = None
    refresh_token_expires_in: int | None = None
    access_token_expires_at: datetime | None = None
    refresh_token_expires_at: datetime | None = None


class CentrifugalRefreshTokenResponseModel(BaseModel):
    id: str
    token: str
    ttl: int


class ExternalIDModel(BaseModel):
    external_id: str | None

    @field_validator("external_id")
    def validate_external_id(cls, v: str | None):
        return v or uuid4()
