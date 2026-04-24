from typing import Optional
from sqlmodel import Relationship
from data.domain.community.schemas import (
    PostBase,
    CommentBase,
    ReactionBase,
    BlockedKeywordBase,
    ModerationLogBase,
    UserBlockBase,
)
from data.lib.model import BaseIDModel


class Post(BaseIDModel, PostBase, table=True):
    user: "User" = Relationship(sa_relationship_kwargs={"lazy": "joined"})  # type: ignore
    comments: list["Comment"] = Relationship(back_populates="post", sa_relationship_kwargs={"lazy": "selectin"})
    reactions: list["Reaction"] = Relationship(
        back_populates="post",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    def __str__(self) -> str:
        title_preview = self.title[:50] if self.title else self.content[:50]
        return f"Post[{self.id}]: {title_preview}..."


class Comment(BaseIDModel, CommentBase, table=True):
    user: "User" = Relationship(sa_relationship_kwargs={"lazy": "joined"})  # type: ignore
    post: Post = Relationship(back_populates="comments", sa_relationship_kwargs={"lazy": "joined"})
    parent_comment: Optional["Comment"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "joined",
            "remote_side": "Comment.id"
        }
    )
    replies: list["Comment"] = Relationship(
        sa_relationship_kwargs={
            "lazy": "selectin",
            "remote_side": "[Comment.parent_comment_id]",
            "cascade": "all, delete-orphan"
        }
    )
    reactions: list["Reaction"] = Relationship(
        back_populates="comment",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan"}
    )

    def __str__(self) -> str:
        content_preview = self.content[:50]
        return f"Comment[{self.id}] on Post[{self.post_id}]: {content_preview}..."


class Reaction(BaseIDModel, ReactionBase, table=True):
    user: "User" = Relationship(sa_relationship_kwargs={"lazy": "joined"})  # type: ignore
    post: Optional[Post] = Relationship(back_populates="reactions", sa_relationship_kwargs={"lazy": "joined"})
    comment: Optional[Comment] = Relationship(back_populates="reactions", sa_relationship_kwargs={"lazy": "joined"})

    def __str__(self) -> str:
        target = f"Post[{self.post_id}]" if self.post_id else f"Comment[{self.comment_id}]"
        return f"Reaction[{self.id}]: {self.type} on {target} by User[{self.user_id}]"


class BlockedKeyword(BaseIDModel, BlockedKeywordBase, table=True):
    def __str__(self) -> str:
        status = "active" if self.active else "inactive"
        return f"BlockedKeyword[{self.id}]: '{self.keyword}' ({status})"


class ModerationLog(BaseIDModel, ModerationLogBase, table=True):
    moderator: Optional["User"] = Relationship(sa_relationship_kwargs={"lazy": "joined"})  # type: ignore

    def __str__(self) -> str:
        mod_name = f"User[{self.moderator_id}]" if self.moderator_id else "System"
        return f"ModerationLog[{self.id}]: {self.action} by {mod_name}"


class UserBlock(BaseIDModel, UserBlockBase, table=True):
    user: "User" = Relationship(sa_relationship_kwargs={"lazy": "joined", "foreign_keys": "UserBlock.user_id"})  # type: ignore
    moderator: "User" = Relationship(sa_relationship_kwargs={"lazy": "joined", "foreign_keys": "UserBlock.moderator_id"})  # type: ignore

    def __str__(self) -> str:
        return f"UserBlock[{self.id}]: User[{self.user_id}] blocked by User[{self.moderator_id}]"
