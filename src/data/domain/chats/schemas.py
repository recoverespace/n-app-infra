from typing import Any
from pydantic import BaseModel
from pydantic.json_schema import SkipJsonSchema
from sqlmodel import Column, Field, SQLModel

from data.domain.intents.state import ChatState
from data.lib.model import pydantic_column_type


class ChatBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    name: str
    state: ChatState = Field(default_factory=ChatState, sa_column=Column(pydantic_column_type(ChatState)))

    def __str__(self) -> str:
        return f"[{self.user_id}]"


class ChatUpdate(ChatBase):
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)


class ChatCreate(ChatBase):
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    state: SkipJsonSchema[Any] = Field(default=None, exclude=True)


class ChatRead(ChatBase):
    id: int
    # state: SkipJsonSchema[Any] = Field(default=None, exclude=True)
