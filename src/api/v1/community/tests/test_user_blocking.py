"""Tests for user blocking functionality"""
import pytest
from httpx import AsyncClient

from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    create_post,
    create_comment,
    block_user,
    test_user,
    second_user,
    test_post,
)


async def test_blocked_user_cannot_post(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocked users cannot create posts"""
    # Block the user
    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="Test blocking"
    )

    # Try to create a post
    payload = {
        "name": "Blocked User Post",
        "body": "This should fail",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }

    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 403, response.text
    assert "blocked" in response.json()["detail"].lower()


async def test_blocked_user_cannot_comment(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test that blocked users cannot create comments"""
    # Block the user
    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="Test blocking"
    )

    # Try to create a comment
    payload = {
        "comment": {
            "body": "This should fail",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 403, response.text
    assert "blocked" in response.json()["detail"].lower()


async def test_blocking_user_hides_their_posts(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocking a user hides all their posts"""
    # User creates posts
    post1 = await create_post(client, test_user, "Post 1", "Content 1")
    post2 = await create_post(client, test_user, "Post 2", "Content 2")

    # Verify posts are visible
    response = await client.get(COMMUNITY_POSTS, headers=second_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 2

    # Block the user
    from data.domain.community import post_crud
    from data.lib.db import SessionLocal

    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="Test blocking"
    )

    # Block all user's posts
    async with SessionLocal() as db:
        await post_crud.block_user_posts(int(test_user.id), tenant_id=0, db=db)

    # Verify posts are now hidden
    response = await client.get(COMMUNITY_POSTS, headers=second_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 0


async def test_blocking_user_hides_their_comments(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocking a user hides all their comments"""
    # Create a post from second user
    post = await create_post(client, second_user, "Post", "Content")

    # First user comments on it
    comment1 = await create_comment(client, test_user, post.id, "Comment 1")
    comment2 = await create_comment(client, test_user, post.id, "Comment 2")

    # Verify comments are visible
    response = await client.get(
        f"{COMMUNITY_POSTS}/{post.id}/comments",
        headers=second_user.token_headers
    )
    data = response.json()
    assert len(data["data"]) == 2

    # Block the user
    from data.domain.community import comment_crud
    from data.lib.db import SessionLocal

    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="Test blocking"
    )

    # Block all user's comments
    async with SessionLocal() as db:
        await comment_crud.block_user_comments(int(test_user.id), tenant_id=0, db=db)

    # Verify comments are now hidden
    response = await client.get(
        f"{COMMUNITY_POSTS}/{post.id}/comments",
        headers=second_user.token_headers
    )
    data = response.json()
    assert len(data["data"]) == 0


async def test_cannot_block_same_user_twice(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocking the same user twice fails"""
    from data.domain.community import user_block_crud
    from data.lib.db import SessionLocal
    from fastapi import HTTPException

    # Block once
    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="First block"
    )

    # Try to block again
    async with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            await user_block_crud.block_user(
                user_id=int(test_user.id),
                moderator_id=int(second_user.id),
                reason="Second block",
                tenant_id=0,
                db=db,
            )
        assert exc_info.value.status_code == 409


async def test_user_block_stores_reason(client: AsyncClient, test_user, second_user) -> None:
    """Test that user blocks store the reason"""
    from data.domain.community import user_block_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import UserBlock

    reason = "Violated community guidelines"

    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason=reason
    )

    # Verify block record exists with reason
    async with SessionLocal() as db:
        block = await user_block_crud.get(
            col(UserBlock.user_id) == int(test_user.id),
            db=db
        )
        assert block is not None
        assert block.reason == reason
        assert block.moderator_id == int(second_user.id)


async def test_is_user_blocked_check(client: AsyncClient, test_user, second_user) -> None:
    """Test the is_user_blocked utility function"""
    from data.domain.community import user_block_crud
    from data.lib.db import SessionLocal

    # User should not be blocked initially
    async with SessionLocal() as db:
        is_blocked = await user_block_crud.is_user_blocked(int(test_user.id), tenant_id=0, db=db)
        assert is_blocked is False

    # Block the user
    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(second_user.id),
        reason="Test"
    )

    # User should now be blocked
    async with SessionLocal() as db:
        is_blocked = await user_block_crud.is_user_blocked(int(test_user.id), tenant_id=0, db=db)
        assert is_blocked is True


async def test_blocking_affects_only_target_user(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocking one user doesn't affect other users"""
    # Both users create posts
    post1 = await create_post(client, test_user, "User 1 Post", "Content 1")
    post2 = await create_post(client, second_user, "User 2 Post", "Content 2")

    # Block first user
    from data.domain.community import post_crud
    from data.lib.db import SessionLocal

    third_user = await init_user(client)
    await block_user(
        user_id=int(test_user.id),
        moderator_id=int(third_user.id),
        reason="Test"
    )

    # Block first user's posts
    async with SessionLocal() as db:
        await post_crud.block_user_posts(int(test_user.id), tenant_id=0, db=db)

    # Only second user's post should be visible
    response = await client.get(COMMUNITY_POSTS, headers=second_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "User 2 Post"


# Import init_user for the last test
from api.lib.tests.utils import init_user


async def test_block_cascade_count(client: AsyncClient, test_user, second_user) -> None:
    """Test that blocking returns count of affected content"""
    from data.domain.community import post_crud, comment_crud
    from data.lib.db import SessionLocal

    # Create multiple posts
    await create_post(client, test_user, "Post 1", "Content")
    await create_post(client, test_user, "Post 2", "Content")
    await create_post(client, test_user, "Post 3", "Content")

    # Create post from another user and add comments from first user
    other_post = await create_post(client, second_user, "Other", "Content")
    await create_comment(client, test_user, other_post.id, "Comment 1")
    await create_comment(client, test_user, other_post.id, "Comment 2")

    # Block user's content
    async with SessionLocal() as db:
        posts_blocked = await post_crud.block_user_posts(int(test_user.id), tenant_id=0, db=db)
        comments_blocked = await comment_crud.block_user_comments(int(test_user.id), tenant_id=0, db=db)

    assert posts_blocked == 3
    assert comments_blocked == 2
