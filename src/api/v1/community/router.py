from fastapi import APIRouter, HTTPException, status, Query
from sqlmodel import col, and_
from datetime import datetime
from collections.abc import Sequence

from api.lib.deps import DBDep, UserIDDep
# Добавляем импорт специфичных ошибок для перехвата
from api.lib.safeguarding import check_text_safe, SafeguardingError, SafeguardingServiceError 
from api.v1.community.schemas import (
    PostDTO,
    PostsResponseDTO,
    CommentDTO,
    CommentsResponseDTO,
    CreatePostPayloadDTO,
    CreateCommentPayloadDTO,
    CreatePostResponseDTO,
    CreateCommentResponseDTO,
    FlagContentPayloadDTO,
    AuthorDTO,
    ReactionResponseDTO,
    ModerationErrorDTO,
)
from data.domain.community import (
    post_crud,
    comment_crud,
    reaction_crud,
    blocked_keyword_crud,
    moderation_log_crud,
    user_block_crud,
)
from data.domain.community.models import Post, Comment
from data.domain.community.schemas import ReactionType, PostCreate, CommentCreate
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from common.otel import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/community", tags=["Community"])


def create_author_dto(user: User) -> AuthorDTO:
    """Convert User model to AuthorDTO"""
    display_name = user.display_name or f"{user.first_name or ''} {user.last_name or ''}".strip() or "Anonymous"
    return AuthorDTO(
        id=user.id,  # type: ignore
        community_member_id=user.id,  # type: ignore
        name=display_name,
        headline="",
        avatar_url=user.avatar_url,
    )


async def convert_post_to_dto(post: Post, user_id: int, db) -> PostDTO:
    """Convert Post model to PostDTO with reaction counts"""
    reaction_counts = await reaction_crud.count_reactions_by_type(post_id=post.id, db=db)
    total_reactions = sum(reaction_counts.values()) + post.anonymous_likes_count

    user_reactions = await reaction_crud.get_user_reactions_for_post(user_id, post.id, db=db)  # type: ignore
    is_liked = len(user_reactions) > 0

    comment_count = await comment_crud.get_count_by(
        condition=and_(
            col(Comment.post_id) == post.id,
            col(Comment.blocked).is_(False)
        ),
        db=db
    )

    return PostDTO(
        id=post.id,  # type: ignore
        name=post.title,
        body=post.content,
        body_plain_text=post.content,
        comment_count=comment_count,
        user_likes_count=total_reactions,
        is_liked=is_liked,
        is_comments_enabled=True,
        is_liking_enabled=True,
        created_at=post.created_at,
        updated_at=post.updated_at,
        author=create_author_dto(post.user),
    )


async def convert_comment_to_dto(comment: Comment, user_id: int, db) -> CommentDTO:
    """Convert Comment model to CommentDTO with reaction counts"""
    reaction_counts = await reaction_crud.count_reactions_by_type(comment_id=comment.id, db=db)
    total_reactions = sum(reaction_counts.values()) + comment.anonymous_likes_count

    user_reactions = await reaction_crud.get_user_reactions_for_comment(user_id, comment.id, db=db)  # type: ignore
    is_liked = len(user_reactions) > 0

    replies_count = await comment_crud.get_count_by(
        condition=and_(
            col(Comment.parent_comment_id) == comment.id,
            col(Comment.blocked).is_(False)
        ),
        db=db
    )

    replies = []
    if replies_count > 0:
        reply_comments = await comment_crud.get_multi(
            condition=and_(
                col(Comment.parent_comment_id) == comment.id,
                col(Comment.blocked).is_(False)
            ),
            limit=100,
            db=db
        )
        for reply in reply_comments:
            replies.append(await convert_comment_to_dto(reply, user_id, db))

    return CommentDTO(
        id=comment.id,  # type: ignore
        post_id=comment.post_id,
        user_id=comment.user_id,
        community_member_id=comment.user_id,
        parent_comment_id=comment.parent_comment_id,
        body_text=comment.content,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        user_likes_count=total_reactions,
        replies_count=replies_count,
        is_liked=is_liked,
        author=create_author_dto(comment.user),
        replies=replies,
    )


@router.get("/posts", response_model=PostsResponseDTO)
async def get_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int = UserIDDep,
    db=DBDep,
) -> PostsResponseDTO:
    """Get paginated list of posts, latest first"""
    skip = (page - 1) * per_page

    posts = await post_crud.get_posts_latest_first(
        skip=skip,
        limit=per_page,
        tenant_id=0,
        include_blocked=False,
        db=db,
    )

    post_dtos = []
    for post in posts:
        post_dto = await convert_post_to_dto(post, user_id, db)
        post_dtos.append(post_dto)

    total = await post_crud.get_count_by(
        condition=and_(
            col(Post.tenant_id) == 0,
            col(Post.blocked).is_(False)
        ),
        db=db
    )

    return PostsResponseDTO(
        data=post_dtos,
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@router.post("/posts", response_model=CreatePostResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: CreatePostPayloadDTO,
    user_id: int = UserIDDep,
    db=DBDep,
) -> CreatePostResponseDTO:
    """Create a new post"""
    if await user_block_crud.is_user_blocked(user_id, tenant_id=0, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked from posting"
        )

    is_blocked, keyword = await blocked_keyword_crud.check_content_for_keywords(
        content=payload.body,
        tenant_id=0,
        db=db
    )

    if is_blocked:
        await moderation_log_crud.log_moderation_action(
            action="keyword_block",
            reason=f"Content contains blocked keyword: {keyword}",
            content_type="post",
            moderator_id=None,
            tenant_id=0,
            meta=f'{{"keyword": "{keyword}", "user_id": {user_id}}}',
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Your post contains inappropriate content: '{keyword}'"
        )

    # --- SAFEGUARDING START ---
    try:
        await check_text_safe(payload.body)
    except SafeguardingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SafeguardingServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    # --- SAFEGUARDING END ---

    post_data = PostCreate(
        tenant_id=0,
        user_id=user_id,
        title=payload.name,
        content=payload.body,
        blocked=False,
    )

    post = await post_crud.create(post_data, db=db)
    user = await user_crud.get(col(User.id) == user_id, db=db)

    return CreatePostResponseDTO(
        id=post.id,  # type: ignore
        name=post.title,
        body=post.content,
        created_at=post.created_at,
        author=create_author_dto(user),  # type: ignore
    )

@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    user_id: int = UserIDDep,
    db=DBDep,
):
    """Delete a post (only by author)"""
    post = await post_crud.get(col(Post.id) == post_id, db=db)

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    if post.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts"
        )

    await post_crud.remove(col(Post.id) == post_id, db=db)
    return None


@router.get("/posts/{post_id}/comments", response_model=CommentsResponseDTO)
async def get_post_comments(
    post_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    user_id: int = UserIDDep,
    db=DBDep,
) -> CommentsResponseDTO:
    """Get paginated comments for a post, oldest first"""
    
    post = await post_crud.get(col(Post.id) == post_id, db=db)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    skip = (page - 1) * per_page

    comments = await comment_crud.get_multi_ordered(
        skip=skip,
        limit=per_page,
        condition=and_(
            col(Comment.post_id) == post_id,
            col(Comment.parent_comment_id).is_(None),
            col(Comment.blocked).is_(False)
        ),
        order_by=[col(Comment.created_at).asc()],
        db=db,
    )

    comment_dtos = []
    for comment in comments:
        comment_dto = await convert_comment_to_dto(comment, user_id, db)
        comment_dtos.append(comment_dto)

    total = await comment_crud.get_count_by(
        condition=and_(
            col(Comment.post_id) == post_id,
            col(Comment.parent_comment_id).is_(None),
            col(Comment.blocked).is_(False)
        ),
        db=db
    )

    return CommentsResponseDTO(
        data=comment_dtos,
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@router.post("/posts/{post_id}/comments", response_model=CreateCommentResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    payload: CreateCommentPayloadDTO,
    user_id: int = UserIDDep,
    db=DBDep,
) -> CreateCommentResponseDTO:
    """Create a comment on a post"""
    if await user_block_crud.is_user_blocked(user_id, tenant_id=0, db=db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been blocked from commenting"
        )

    post = await post_crud.get(col(Post.id) == post_id, db=db)
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    comment_body = payload.comment.get("body", "")
    if not comment_body:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment body is required")

    is_blocked, keyword = await blocked_keyword_crud.check_content_for_keywords(
        content=comment_body,
        tenant_id=0,
        db=db
    )

    if is_blocked:
        await moderation_log_crud.log_moderation_action(
            action="keyword_block",
            reason=f"Content contains blocked keyword: {keyword}",
            content_type="comment",
            moderator_id=None,
            tenant_id=0,
            meta=f'{{"keyword": "{keyword}", "user_id": {user_id}}}',
            db=db
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Your comment contains inappropriate content: '{keyword}'"
        )

    # --- SAFEGUARDING START ---
    try:
        await check_text_safe(comment_body)
    except SafeguardingError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SafeguardingServiceError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    # --- SAFEGUARDING END ---

    comment_data = CommentCreate(
        tenant_id=0,
        post_id=post_id,
        user_id=user_id,
        parent_comment_id=None,
        content=comment_body,
        blocked=False,
    )

    comment = await comment_crud.create(comment_data, db=db)
    user = await user_crud.get(col(User.id) == user_id, db=db)

    return CreateCommentResponseDTO(
        id=comment.id,  # type: ignore
        post_id=post_id,
        body_text=comment.content,
        created_at=comment.created_at,
        author=create_author_dto(user),  # type: ignore
    )


@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    post_id: int,
    comment_id: int,
    user_id: int = UserIDDep,
    db=DBDep,
):
    """Delete a comment (only by author)"""
    comment = await comment_crud.get(col(Comment.id) == comment_id, db=db)

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    if comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments"
        )

    await comment_crud.remove(col(Comment.id) == comment_id, db=db)
    return None


@router.post("/posts/{post_id}/user_likes", response_model=ReactionResponseDTO)
async def add_post_reaction(
    post_id: int,
    user_id: int = UserIDDep,
    reaction_type: ReactionType = ReactionType.like,
    db=DBDep,
) -> ReactionResponseDTO:
    """Add a 'like' reaction to a post (Circle.so compatible endpoint)"""
    post = await post_crud.get(col(Post.id) == post_id, db=db)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    try:
        await reaction_crud.add_reaction(
            user_id=user_id,
            reaction_type=reaction_type,
            post_id=post_id,
            tenant_id=0,
            db=db
        )
        return ReactionResponseDTO(success=True, message=f"{reaction_type} added successfully")
    except HTTPException as e:
        raise e


@router.delete("/posts/{post_id}/user_likes", response_model=ReactionResponseDTO)
async def remove_post_reaction(
    post_id: int,
    user_id: int = UserIDDep,
    reaction_type: ReactionType = ReactionType.like,
    db=DBDep,
) -> ReactionResponseDTO:
    """Remove a 'like' reaction from a post (Circle.so compatible endpoint)"""
    success = await reaction_crud.remove_reaction(
        user_id=user_id,
        reaction_type=reaction_type,
        post_id=post_id,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )

    return ReactionResponseDTO(success=True, message=f"{reaction_type} removed successfully")


@router.post("/posts/{post_id}/comments/{comment_id}/user_likes", response_model=ReactionResponseDTO)
async def add_comment_reaction(
    post_id: int,
    comment_id: int,
    user_id: int = UserIDDep,
    reaction_type: ReactionType = ReactionType.like,
    db=DBDep,
) -> ReactionResponseDTO:
    """Add a 'like' reaction to a comment (Circle.so compatible endpoint)"""
    post = await post_crud.get(col(Post.id) == post_id, db=db)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    comment = await comment_crud.get(col(Comment.id) == comment_id, db=db)
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )

    try:
        await reaction_crud.add_reaction(
            user_id=user_id,
            reaction_type=reaction_type,
            post_id=post_id,
            comment_id=comment_id,
            tenant_id=0,
            db=db
        )
        return ReactionResponseDTO(success=True, message=f"{reaction_type} added successfully")
    except HTTPException as e:
        raise e


@router.delete("/posts/{post_id}/comments/{comment_id}/user_likes", response_model=ReactionResponseDTO)
async def remove_comment_reaction(
    post_id: int,
    comment_id: int,
    user_id: int = UserIDDep,
    reaction_type: ReactionType = ReactionType.like,
    db=DBDep,
) -> ReactionResponseDTO:
    """Remove a 'like' reaction from a comment (Circle.so compatible endpoint)"""
    success = await reaction_crud.remove_reaction(
        user_id=user_id,
        reaction_type=reaction_type,
        post_id=post_id,
        comment_id=comment_id,
        db=db
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reaction not found"
        )

    return ReactionResponseDTO(success=True, message=f"{reaction_type} removed successfully")


@router.post("/flagged_contents", status_code=status.HTTP_201_CREATED)
async def flag_content(
    payload: FlagContentPayloadDTO,
    user_id: int = UserIDDep,
    db=DBDep,
):
    """Flag content for moderation review"""
    if payload.content_type == "post":
        content = await post_crud.get(col(Post.id) == payload.content_id, db=db)
    elif payload.content_type == "comment":
        content = await comment_crud.get(col(Comment.id) == payload.content_id, db=db)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Must be 'post' or 'comment'"
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{payload.content_type.capitalize()} not found"
        )

    await moderation_log_crud.log_moderation_action(
        action="content_flag",
        reason=payload.reason,
        content_type=payload.content_type,
        content_id=payload.content_id,
        moderator_id=user_id,  # User who flagged
        tenant_id=0,
        meta=f'{{"flagged_by": {user_id}}}',
        db=db
    )

    return {"success": True, "message": "Content flagged for review"}
