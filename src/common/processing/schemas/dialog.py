from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field


class DialogMessage(BaseModel):
    user_id: int
    chat_id: int
    message_id: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[Any] = Field(default_factory=list)
    intent: str | None = None
    handler: str | None = None
    source: str = "api"
    params: dict[str, Any] = Field(default_factory=dict)


class DialogResponseMessage(BaseModel):
    user_id: int
    chat_id: int
    original_message_id: int | None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    items: list[Any]

class DialogTriggerMessage(BaseModel):
    user_id: int
    chat_id: int
    kind: str | None
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DialogActionMessage(BaseModel):
    id: str | None = None
    kind: str | None = None
    state: str | None = None
    action_type: Any | None = None
    user_id: int
    chat_id: int
    extra: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DialogRunIntentRequest(BaseModel):
    user_id: int
    chat_id: int
    intent: str
    handler: str
    params: dict[str, Any] = Field(default_factory=dict)
    text: str = ""


class DialogIntentRequest(BaseModel):
    user_id: int
    chat_id: int
    intent: str
    text: str
    last_facts: dict[str, list]
    last_messages: list[tuple[str, str]]
    user: str


class DialogIntentResponse(BaseModel):
    user_id: int
    chat_id: int
    intent: str
    messages: list[str]
