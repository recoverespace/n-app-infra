from sqlmodel import SQLModel, Field


class PostBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str | None = Field(default=None, max_length=500, description="Optional post title")
    content: str = Field(description="Post content/message")
    blocked: bool = Field(default=False, index=True, description="Whether post is blocked by moderators")
    anonymous_likes_count: int = Field(default=0, description="Count of likes from unknown/unmapped users")


class PostCreate(PostBase):
    pass


class PostUpdate(SQLModel):
    title: str | None = None
    content: str | None = None
    blocked: bool | None = None
    anonymous_likes_count: int | None = None
