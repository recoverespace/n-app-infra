from sqlmodel import SQLModel, Field


class CommentBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    post_id: int = Field(foreign_key="post.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    parent_comment_id: int | None = Field(default=None, foreign_key="comment.id", index=True, description="For nested replies")
    content: str = Field(description="Comment content/message")
    blocked: bool = Field(default=False, index=True, description="Whether comment is blocked by moderators")
    anonymous_likes_count: int = Field(default=0, description="Count of likes from unknown/unmapped users")


class CommentCreate(CommentBase):
    pass


class CommentUpdate(SQLModel):
    content: str | None = None
    blocked: bool | None = None
    anonymous_likes_count: int | None = None
