from datetime import datetime
from sqlmodel import SQLModel, Field, Column, DateTime


class ChatNotification(SQLModel):
    sent_at: datetime | None = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    message: str
    title: str | None
    data: list[str] | None
    image: str | None
