from datetime import datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict
from .attachments import Attachment
from .notification import ChatNotification
from .suggestions import Suggestions
from sqlmodel import SQLModel, Field, Column, String, DateTime
from pydantic.json_schema import SkipJsonSchema
from uuid import UUID, uuid4
from data.lib.model import pydantic_column_type

from .reaction import MessageReactionRead
# from uuid_utils import uuid7


class MessageType(StrEnum):
    message = "message"
    suggestion = "suggestion"
    recommendation = "recommendation"


class ActionType(StrEnum):
    user_input = "user_input"
    suggestion = "suggestion"
    app_open = "app_open"
    api_call = "api_call"
    llm_answer = "llm_answer"
    emotion_selected = "emotion_selected"


class MessageActionType(StrEnum):
    create = "create"
    update = "update"
    delete = "delete"
    ack = "ack"


class ChatActionType(StrEnum):
    typing = "typing"
    suggesting = "suggesting"
    not_typing = "not_typing"
    proactivity = "proactivity"


class ExtraData(BaseModel):
    label: str
    screen: str
    params: dict[str, Any] = Field(default_factory=dict)


class ExtraAction(BaseModel):
    kind: str
    data: ExtraData


class ExtraProactivity(BaseModel):
    id: str
    kind: str
    state: str = ""
    step: int = 1
    max_steps: int = 1


class UserOption(BaseModel):
    label: str
    value: str


class Extra(BaseModel):
    is_likes_available: bool = False
    user_action_type: ActionType = ActionType.user_input
    used_intent: str | None = None
    proactivity: ExtraProactivity | None = None
    data: dict[str, Any] | None = Field(default_factory=dict)
    ai_suggestions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default_factory=dict)
    actions: list[ExtraAction] = Field(default_factory=list)
    selected_options: list[UserOption] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ChatMessageBase(SQLModel):
    chat_id: int | None = Field(foreign_key="chat.id", default=None)
    user_id: int | None = Field(foreign_key="user.id", default=None)
    uid: UUID = Field(default_factory=uuid4, index=True, nullable=False)
    text: str = ""
    role: str | None = "user"
    trace_id: str | None = None
    intent_used: str | None = None
    notification: ChatNotification | None = Field(
        default=None, sa_column=Column(pydantic_column_type(ChatNotification))
    )
    scheduled_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    message_type: MessageType = Field(default=MessageType.message, sa_column=Column(String))
    attachments: list[Attachment] = Field(
        default_factory=list, sa_column=Column(pydantic_column_type(list[Attachment]))
    )
    suggestions: Suggestions | None = Field(
        default_factory=Suggestions, sa_column=Column(pydantic_column_type(Suggestions))
    )
    extra: Extra = Field(default_factory=dict, sa_column=Column(pydantic_column_type(Extra)))
    acked_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    def __str__(self) -> str:
        return f"{self.text} [{self.chat_id}]"


class ChatMessageUpdate(ChatMessageBase): ...


class ChatMessageCreate(ChatMessageBase):
    chat_id: SkipJsonSchema[int | None] = Field(default=1, exclude=True)
    user_id: SkipJsonSchema[int | None] = Field(default=1, exclude=True)
    attachments: list[Attachment] | None = Field(default_factory=list)
    suggestions: Suggestions | None = Field(default_factory=Suggestions)
    extra: Extra = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore", missing="ignore")  # type: ignore


class ChatMessageRead(ChatMessageBase):
    id: int
    reactions: list[MessageReactionRead]
    created_at: datetime
    updated_at: datetime