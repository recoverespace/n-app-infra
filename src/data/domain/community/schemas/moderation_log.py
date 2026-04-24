from enum import StrEnum
from sqlmodel import SQLModel, Field


class ModerationType(StrEnum):
    keyword_block = "keyword_block"
    user_block = "user_block"
    content_flag = "content_flag"
    post_delete = "post_delete"
    comment_delete = "comment_delete"


class ModerationLogBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    content_type: str | None = Field(default=None, max_length=50, description="Type of content: post, comment, or user")
    content_id: int | None = Field(default=None, description="ID of the content being moderated")
    action: ModerationType = Field(description="Type of moderation action taken")
    reason: str = Field(description="Reason for moderation action")
    moderator_id: int | None = Field(default=None, foreign_key="user.id", index=True, description="Admin/moderator who took action")
    meta: str | None = Field(default=None, description="Additional meta as JSON string")


class ModerationLogCreate(ModerationLogBase):
    pass


class ModerationLogUpdate(SQLModel):
    reason: str | None = None
    meta: str | None = None
