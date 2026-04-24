from enum import StrEnum
from pydantic import ConfigDict
from sqlmodel import SQLModel, Field, Column, String
from pydantic.json_schema import SkipJsonSchema


class ReactionType(StrEnum):
    like = "like"
    dislike = "dislike"


class MessageReactionBase(SQLModel):
    chat_id: int = Field(foreign_key="chat.id")
    user_id: int = Field(foreign_key="user.id")
    chat_message_id: int = Field(foreign_key="chatmessage.id")
    reaction_type: ReactionType = Field(default=ReactionType.like, sa_column=Column(String))

    model_config = ConfigDict(from_attributes=True) # type: ignore

    def __str__(self) -> str:
        return f"{self.reaction_type} [{self.chat_message_id}]"


class MessageReactionUpdate(MessageReactionBase):
    chat_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    chat_message_id: SkipJsonSchema[int] = Field(default=1, exclude=True)


class MessageReactionCreate(MessageReactionBase):
    chat_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    chat_message_id: SkipJsonSchema[int] = Field(default=1, exclude=True)


class MessageReactionRead(MessageReactionBase):
    id: int
