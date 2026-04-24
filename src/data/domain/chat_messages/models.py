from sqlmodel import Relationship
from data.domain.chat_messages.schemas import (
    ChatMessageBase,
    MessageReactionBase,
    MessageFeedbackBase,
)
from data.domain.chats.models import Chat
from data.domain.users.models import User
from data.lib.model import BaseIDModel


class ChatMessage(BaseIDModel, ChatMessageBase, table=True):
    chat: Chat = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    reactions: list["MessageReaction"] = Relationship(
        back_populates="chat_message", sa_relationship_kwargs={"lazy": "joined"}
    )


class MessageReaction(BaseIDModel, MessageReactionBase, table=True):
    chat_message: ChatMessage = Relationship(back_populates="reactions")


class MessageFeedback(BaseIDModel, MessageFeedbackBase, table=True):
    user: User = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    chat: Chat = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    chat_message: ChatMessage = Relationship(sa_relationship_kwargs={"lazy": "joined"})
