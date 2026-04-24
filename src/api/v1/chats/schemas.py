from datetime import UTC, datetime

from pydantic import BaseModel, Field

from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas.message import ChatActionType, MessageActionType, MessageType


class CentrifugeMessageModel(BaseModel):
    state: str | None = None
    action_type: MessageActionType = MessageActionType.create
    chat_id: int | None = None
    message_id: int | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message_type: MessageType = MessageType.message
    items: list[ChatMessage] | None = None


class CentrifugeTypingModel(BaseModel):
    chat_id: int | None = None
    user_id: int | None = None
    action_type: ChatActionType = ChatActionType.typing


class CentrifugeProactivityModel(BaseModel):
    id: str
    kind: str
    state: str
    action_type: str = "proactivity"


class CentrifugeInfoModel(BaseModel):
    connection_url: str
    channel_name: str


class ChatMessageAckModel(BaseModel):
    acked_at: datetime = Field(default_factory=datetime.now)


class ChatFileUploadModel(BaseModel):
    url: str
