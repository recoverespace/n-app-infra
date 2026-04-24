from enum import StrEnum
from sqlmodel import SQLModel, Field


class ReactionType(StrEnum):
    like = "like"
    salute = "salute"
    hug = "hug"


class ReactionBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    user_id: int = Field(foreign_key="user.id", index=True)
    post_id: int | None = Field(default=None, foreign_key="post.id", index=True)
    comment_id: int | None = Field(default=None, foreign_key="comment.id", index=True)
    type: ReactionType = Field(description="Type of reaction: like, salute, or hug")


class ReactionCreate(ReactionBase):
    pass


class ReactionUpdate(SQLModel):
    type: ReactionType | None = None
