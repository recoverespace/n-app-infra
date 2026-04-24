from datetime import date, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Column, DateTime, SQLModel, Field

from data.domain.chat_messages.models import ChatMessage


class Fact(BaseModel):
    value: str
    source: str
    expires_at: datetime


class Goal(BaseModel):
    name: str
    priority: int
    completed: bool = False
    id: UUID = Field(default_factory=uuid4)

    def __str__(self):
        return f"{self.name}{' (completed)' if self.completed else ''}"


class Memory(BaseModel):
    capacity: int = 10
    default_ttl: int = 60 * 60
    memory: dict[str, Fact] = Field(default_factory=dict)

    def clean_up(self):
        now = datetime.now()
        for key, value in self.memory.items():
            if value.expires_at < now:
                del self.memory[key]

    def add(self, key: str, value: str, source: str, ttl: int | None = None):
        self.clean_up()
        if len(self.memory) > self.capacity:  # Delete oldest memory if memory is full
            oldest_key = min(self.memory, key=lambda k: self.memory[k].expires_at)
            del self.memory[oldest_key]
        ttl = ttl or self.default_ttl
        self.memory[key] = Fact(
            value=value, source=source, expires_at=datetime.now() + timedelta(seconds=ttl)
        )

    def set(self, key: str, value: str, source: str, ttl: int | None = None):
        ttl = ttl or self.default_ttl
        self.memory[key] = Fact(
            value=value, source=source, expires_at=datetime.now() + timedelta(seconds=ttl)
        )

    def get(self, key: str) -> str:
        self.clean_up()
        fact = self.memory.get(key)
        if fact:
            return fact.value
        return ""


class UserContext(BaseModel):
    first_name: str
    full_name: str
    conception_date: date
    last_message: str = ""
    conversation_summary: str = ""
    memory: dict[str, Memory] = Field(default_factory=dict)
    facts: list[Fact] = Field(default_factory=list)
    goals: list[Goal] = Field(default_factory=list)


class ChatTriggerType(StrEnum):
    text = "text"
    voice = "voice"
    image = "image"
    external = "external"


class SelectedAgent(BaseModel):
    name: str
    goal: str
    reason: str


class ChatTrigger(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: ChatTriggerType
    start_time: datetime = Field(
        default_factory=datetime.now, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    agent: SelectedAgent | None = None
    agent_step: str | None = None
    context: UserContext
    message: ChatMessage
    goals: list[Goal] = Field(default_factory=list)

    def add_goal(self, goal: Goal):
        self.goals.append(goal)


class TemplateOverrideBase(SQLModel):
    template_name: str
    user_id: int | None = Field(foreign_key="user.id")
    segment: str | None = None
    intent_name: str | None = None
    suffix: str | None = None
    content: str | None = None


class TemplateOverrideCreate(TemplateOverrideBase): ...


class TemplateOverrideUpdate(TemplateOverrideBase): ...
