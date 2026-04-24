from datetime import datetime
from sqlmodel import SQLModel, Field, Column, Text, DateTime


class DeviceBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    installed_at: datetime | None = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    conversion_data: str | None = Field(sa_column=Column(Text))
    os: str | None = None
    platform: str | None = None
    store: str | None = None
    timezone: str | None = None
    limited_ad_tracking: bool = False
    device_model: str | None = None
    app_version: str | None = None
    idfa: str | None = None
    idfv: str | None = None
    language: str | None = None


class DeviceUpdate(DeviceBase): ...


class DeviceCreate(DeviceBase): ...


class DeviceRead(DeviceBase):
    id: int
