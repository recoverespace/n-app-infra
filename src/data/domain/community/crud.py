from sqlmodel import col, select, func, and_
from sqlmodel.ext.asyncio.session import AsyncSession
from data.domain.community.schemas import (
    PostCreate,
    PostUpdate,
    CommentCreate,
    CommentUpdate,
    ReactionCreate,
    ReactionUpdate,
    BlockedKeywordCreate,
    BlockedKeywordUpdate,
    ModerationLogCreate,
    ModerationLogUpdate,
    UserBlockCreate,
    UserBlockUpdate,
    ReactionType,
)
from data.domain.community.models import Post, Comment, Reaction, BlockedKeyword, ModerationLog, UserBlock
from data.lib.crud import CRUDBase
from typing import Sequence
from fastapi import HTTPException, status


class CRUDPost(CRUDBase[Post, PostCreate, PostUpdate]):
    async def get_posts_latest_first(
        self,
        skip: int = 0,
        limit: int = 100,
        tenant_id: int = 0,
        include_blocked: bool = False,
        db: AsyncSession | None = None,
    ) -> Sequence[Post]:
        """Get posts ordered by latest first (descending created_at)"""
        session = self.get_db(db)

        condition = col(Post.tenant_id) == tenant_id
        if not include_blocked:
            condition = and_(condition, col(Post.blocked).is_(False))

        query = (
            select(Post)
            .where(condition)
            .order_by(col(Post.created_at).desc())
            .offset(skip)
            .limit(limit)
        )

        response = await session.exec(query)
        return response.unique().all()

    async def get_user_posts(
        self,
        user_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> Sequence[Post]:
        """Get all posts by a specific user"""
        session = self.get_db(db)

        query = (
            select(Post)
            .where(
                and_(
                    col(Post.user_id) == user_id,
                    col(Post.tenant_id) == tenant_id
                )
            )
            .order_by(col(Post.created_at).desc())
        )

        response = await session.exec(query)
        return response.unique().all()

    async def block_user_posts(
        self,
        user_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> int:
        """Block all posts by a specific user, returns count of blocked posts"""
        session = self.get_db(db)

        posts = await self.get_user_posts(user_id=user_id, tenant_id=tenant_id, db=session)

        count = 0
        for post in posts:
            if not post.blocked:
                post.blocked = True
                session.add(post)
                count += 1

        await session.commit()
        return count


class CRUDComment(CRUDBase[Comment, CommentCreate, CommentUpdate]):
    async def get_post_comments(
        self,
        post_id: int,
        skip: int = 0,
        limit: int = 100,
        include_blocked: bool = False,
        db: AsyncSession | None = None,
    ) -> Sequence[Comment]:
        """Get comments for a post ordered by oldest first (ascending created_at)"""
        session = self.get_db(db)

        condition = col(Comment.post_id) == post_id
        if not include_blocked:
            condition = and_(condition, col(Comment.blocked).is_(False))

        query = (
            select(Comment)
            .where(condition)
            .order_by(col(Comment.created_at).asc())
            .offset(skip)
            .limit(limit)
        )

        response = await session.exec(query)
        return response.unique().all()

    async def get_user_comments(
        self,
        user_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> Sequence[Comment]:
        """Get all comments by a specific user"""
        session = self.get_db(db)

        query = (
            select(Comment)
            .where(
                and_(
                    col(Comment.user_id) == user_id,
                    col(Comment.tenant_id) == tenant_id
                )
            )
            .order_by(col(Comment.created_at).desc())
        )

        response = await session.exec(query)
        return response.unique().all()

    async def block_user_comments(
        self,
        user_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> int:
        """Block all comments by a specific user, returns count of blocked comments"""
        session = self.get_db(db)

        comments = await self.get_user_comments(user_id=user_id, tenant_id=tenant_id, db=session)

        count = 0
        for comment in comments:
            if not comment.blocked:
                comment.blocked = True
                session.add(comment)
                count += 1

        await session.commit()
        return count


class CRUDReaction(CRUDBase[Reaction, ReactionCreate, ReactionUpdate]):
    async def get_user_reactions_for_post(
        self,
        user_id: int,
        post_id: int,
        db: AsyncSession | None = None,
    ) -> Sequence[Reaction]:
        """Get all reactions by a user on a specific post"""
        session = self.get_db(db)

        query = select(Reaction).where(
            and_(
                col(Reaction.user_id) == user_id,
                col(Reaction.post_id) == post_id
            )
        )

        response = await session.exec(query)
        return response.all()

    async def get_user_reactions_for_comment(
        self,
        user_id: int,
        comment_id: int,
        db: AsyncSession | None = None,
    ) -> Sequence[Reaction]:
        """Get all reactions by a user on a specific comment"""
        session = self.get_db(db)

        query = select(Reaction).where(
            and_(
                col(Reaction.user_id) == user_id,
                col(Reaction.comment_id) == comment_id
            )
        )

        response = await session.exec(query)
        return response.all()

    async def count_reactions_by_type(
        self,
        post_id: int | None = None,
        comment_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> dict[str, int]:
        """Count reactions by type for a post or comment"""
        session = self.get_db(db)

        if post_id:
            condition = col(Reaction.post_id) == post_id
        elif comment_id:
            condition = col(Reaction.comment_id) == comment_id
        else:
            return {}

        query = (
            select(Reaction.type, func.count(Reaction.id))
            .where(condition)
            .group_by(Reaction.type)
        )

        response = await session.exec(query)
        results = response.all()

        return {reaction_type: count for reaction_type, count in results}

    async def validate_reaction_limit(
        self,
        user_id: int,
        post_id: int | None = None,
        comment_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> bool:
        """Check if user has reached the 3 reaction limit"""
        session = self.get_db(db)

        if post_id:
            reactions = await self.get_user_reactions_for_post(user_id, post_id, session)
        elif comment_id:
            reactions = await self.get_user_reactions_for_comment(user_id, comment_id, session)
        else:
            return False

        return len(reactions) < 3

    async def add_reaction(
        self,
        user_id: int,
        reaction_type: ReactionType,
        post_id: int | None = None,
        comment_id: int | None = None,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> Reaction:
        """Add a reaction with validation"""
        session = self.get_db(db)

        # Check if user already has this reaction type
        if post_id:
            existing = await session.exec(
                select(Reaction).where(
                    and_(
                        col(Reaction.user_id) == user_id,
                        col(Reaction.post_id) == post_id,
                        col(Reaction.type) == reaction_type
                    )
                )
            )
        else:
            existing = await session.exec(
                select(Reaction).where(
                    and_(
                        col(Reaction.user_id) == user_id,
                        col(Reaction.comment_id) == comment_id,
                        col(Reaction.type) == reaction_type
                    )
                )
            )

        if existing.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a {reaction_type} reaction on this content"
            )

        # Validate 3 reaction limit
        if not await self.validate_reaction_limit(user_id, post_id, comment_id, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum of 3 reactions per post/comment reached"
            )

        # Create the reaction
        reaction_data = ReactionCreate(
            tenant_id=tenant_id,
            user_id=user_id,
            post_id=post_id,
            comment_id=comment_id,
            type=reaction_type
        )

        return await self.create(reaction_data, session)

    async def remove_reaction(
        self,
        user_id: int,
        reaction_type: ReactionType,
        post_id: int | None = None,
        comment_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> bool:
        """Remove a specific reaction type"""
        session = self.get_db(db)

        if post_id:
            condition = and_(
                col(Reaction.user_id) == user_id,
                col(Reaction.post_id) == post_id,
                col(Reaction.type) == reaction_type
            )
        else:
            condition = and_(
                col(Reaction.user_id) == user_id,
                col(Reaction.comment_id) == comment_id,
                col(Reaction.type) == reaction_type
            )

        try:
            await self.remove(condition, session)
            return True
        except Exception:
            return False


class CRUDBlockedKeyword(CRUDBase[BlockedKeyword, BlockedKeywordCreate, BlockedKeywordUpdate]):
    async def get_active_keywords(
        self,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> Sequence[BlockedKeyword]:
        """Get all active blocked keywords for a tenant"""
        session = self.get_db(db)

        query = select(BlockedKeyword).where(
            and_(
                col(BlockedKeyword.tenant_id) == tenant_id,
                col(BlockedKeyword.active).is_(True)
            )
        )

        response = await session.exec(query)
        return response.all()

    async def check_content_for_keywords(
        self,
        content: str,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> tuple[bool, str | None]:
        """
        Check if content contains any blocked keywords.
        Returns (is_blocked, keyword_found)
        """
        session = self.get_db(db)
        keywords = await self.get_active_keywords(tenant_id, session)

        content_lower = content.lower()

        for keyword in keywords:
            # Whole word matching
            keyword_lower = keyword.keyword.lower()
            if keyword_lower in content_lower:
                # Check if it's a whole word (not part of another word)
                import re
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, content_lower):
                    return (True, keyword.keyword)

        return (False, None)


class CRUDModerationLog(CRUDBase[ModerationLog, ModerationLogCreate, ModerationLogUpdate]):
    async def log_moderation_action(
        self,
        action: str,
        reason: str,
        content_type: str | None = None,
        content_id: int | None = None,
        moderator_id: int | None = None,
        tenant_id: int = 0,
        meta: str | None = None,
        db: AsyncSession | None = None,
    ) -> ModerationLog:
        """Create a moderation log entry"""
        session = self.get_db(db)

        log_data = ModerationLogCreate(
            tenant_id=tenant_id,
            content_type=content_type,
            content_id=content_id,
            action=action,  # type: ignore
            reason=reason,
            moderator_id=moderator_id,
            meta=meta
        )

        return await self.create(log_data, session)


class CRUDUserBlock(CRUDBase[UserBlock, UserBlockCreate, UserBlockUpdate]):
    async def is_user_blocked(
        self,
        user_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> bool:
        """Check if a user is blocked"""
        session = self.get_db(db)

        result = await session.exec(
            select(UserBlock).where(
                and_(
                    col(UserBlock.user_id) == user_id,
                    col(UserBlock.tenant_id) == tenant_id
                )
            )
        )

        return result.first() is not None

    async def block_user(
        self,
        user_id: int,
        reason: str,
        moderator_id: int,
        tenant_id: int = 0,
        db: AsyncSession | None = None,
    ) -> UserBlock:
        """Block a user and their content"""
        session = self.get_db(db)

        # Check if already blocked
        if await self.is_user_blocked(user_id, tenant_id, session):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already blocked"
            )

        # Create block record
        block_data = UserBlockCreate(
            tenant_id=tenant_id,
            user_id=user_id,
            reason=reason,
            moderator_id=moderator_id
        )

        return await self.create(block_data, session)


# Create CRUD instances
post_crud = CRUDPost(Post)
comment_crud = CRUDComment(Comment)
reaction_crud = CRUDReaction(Reaction)
blocked_keyword_crud = CRUDBlockedKeyword(BlockedKeyword)
moderation_log_crud = CRUDModerationLog(ModerationLog)
user_block_crud = CRUDUserBlock(UserBlock)
