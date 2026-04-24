from datetime import datetime
from pydantic import BaseModel, Field
from data.domain.community.schemas import ReactionType


# Author DTOs matching Circle.so format
class AuthorDTO(BaseModel):
    id: int
    community_member_id: int  # Same as user_id for compatibility
    name: str
    headline: str = ""
    avatar_url: str | None = None

    class Config:
        from_attributes = True


# Post DTOs matching Circle.so format
class PostDTO(BaseModel):
    id: int
    name: str | None = None  # title
    body: str  # content
    body_plain_text: str  # content (same as body for simple text)
    comment_count: int = 0
    user_likes_count: int = 0  # Total reactions count
    is_liked: bool = False
    is_comments_enabled: bool = True
    is_liking_enabled: bool = True
    created_at: datetime
    updated_at: datetime
    author: AuthorDTO

    class Config:
        from_attributes = True


class PostsResponseDTO(BaseModel):
    data: list[PostDTO]
    meta: dict[str, int]  # {total, page, per_page}


# Comment DTOs matching Circle.so format
class CommentDTO(BaseModel):
    id: int
    post_id: int
    user_id: int
    community_member_id: int  # Same as user_id for compatibility
    parent_comment_id: int | None = None
    body_text: str  # content
    created_at: datetime
    updated_at: datetime
    user_likes_count: int = 0
    replies_count: int = 0
    is_liked: bool = False
    author: AuthorDTO
    replies: list["CommentDTO"] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CommentsResponseDTO(BaseModel):
    data: list[CommentDTO]
    meta: dict[str, int]  # {total, page, per_page}


# Create Post payload (from frontend)
class CreatePostPayloadDTO(BaseModel):
    name: str | None = None  # title
    body: str  # content
    is_comments_enabled: bool = True
    is_liking_enabled: bool = True


# Create Comment payload (from frontend)
class CreateCommentPayloadDTO(BaseModel):
    comment: dict[str, str]  # {"body": "content"}


# Flag Content payload
class FlagContentPayloadDTO(BaseModel):
    content_type: str  # "post" or "comment"
    content_id: int
    reason: str


# Pagination params
class PaginationParamsDTO(BaseModel):
    page: int = 1
    per_page: int = 20


# Response models for creating content
class CreatePostResponseDTO(BaseModel):
    id: int
    name: str | None
    body: str
    created_at: datetime
    author: AuthorDTO

    class Config:
        from_attributes = True


class CreateCommentResponseDTO(BaseModel):
    id: int
    post_id: int
    body_text: str
    created_at: datetime
    author: AuthorDTO

    class Config:
        from_attributes = True


# Reaction response
class ReactionResponseDTO(BaseModel):
    success: bool = True
    message: str | None = None


# Error response for moderation
class ModerationErrorDTO(BaseModel):
    error: str
    keyword: str | None = None
    detail: str
