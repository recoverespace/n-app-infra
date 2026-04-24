from datetime import datetime
from pydantic import BaseModel, Field
from enum import StrEnum


class SortOrder(StrEnum):
    asc = "asc"
    desc = "desc"


class BaseFilter(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=50, ge=1, le=100)
    start_date: datetime | None = None
    end_date: datetime | None = None
    sort_by: str | None = None
    sort_order: SortOrder = SortOrder.desc


class UserFilter(BaseFilter):
    user_id: int | None = None
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    is_active: bool | None = None
    is_deleted: bool = True
    is_onboarding_finished: bool | None = None
    notifications_enabled: bool | None = None
    is_migrated_user: bool | None = None
    source: str | None = None


class FactFilter(BaseFilter):
    user_id: int | None = None
    kind: str | None = None


class ChatFilter(BaseFilter):
    user_id: int | None = None


class MessageFilter(BaseFilter):
    user_id: int | None = None
    chat_id: int | None = None

class FactFilter(BaseFilter):
    user_id: int | None = None
    kind: str | None = None
    label: str | None = None

class PaginatedResponse(BaseModel):
    items: list[dict]
    page: int
    size: int