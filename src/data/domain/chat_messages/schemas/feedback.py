from sqlmodel import SQLModel, Field, Column, JSON
from pydantic.json_schema import SkipJsonSchema


class MessageFeedbackBase(SQLModel):
    chat_id: int = Field(foreign_key="chat.id")
    user_id: int = Field(foreign_key="user.id")
    chat_message_id: int = Field(foreign_key="chatmessage.id")
    text: str
    options: list[str] = Field(default_factory=list, sa_column=Column(JSON))

    def __str__(self) -> str:
        return f"{self.text} [{self.chat_message_id}]"


class MessageFeedbackUpdate(MessageFeedbackBase):
    chat_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    chat_message_id: SkipJsonSchema[int] = Field(default=1, exclude=True)


class MessageFeedbackCreate(MessageFeedbackBase):
    chat_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    user_id: SkipJsonSchema[int] = Field(default=1, exclude=True)
    chat_message_id: SkipJsonSchema[int] = Field(default=1, exclude=True)


class MessageFeedbackRead(MessageFeedbackBase):
    id: int
