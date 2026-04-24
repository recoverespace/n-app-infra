from enum import StrEnum
from typing import Any
from sqlmodel import SQLModel, Field, JSON, Column, String
from data.settings import settings


class StaticContentTypes(StrEnum):
    audio = "audio"
    voice = "voice"
    file = "file"
    image = "image"
    external_link = "external-link"


class StaticFileBase(SQLModel):
    group: str
    path: str
    content_type: StaticContentTypes = Field(default=StaticContentTypes.file, sa_column=Column(String))
    extra: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))

    def get_url(self, chat_id:int) -> str:
        return f"{settings.EXTERNAL_URL}/v1/chats/{chat_id}/media/{self.path}"


class StaticFileUpdate(StaticFileBase): ...


class StaticFileCreate(StaticFileBase): ...


class StaticFileRead(StaticFileBase):
    id: int
