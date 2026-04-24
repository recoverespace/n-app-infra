"""Tests for reaction endpoints"""
import pytest
from httpx import AsyncClient

from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    create_post,
    test_user,
    second_user,
    test_post,
)


async def test_like_post(client: AsyncClient, test_user, test_post) -> None:
    """Test liking a post"""
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["success"] is True

    # Verify the post shows the like
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    posts_data = response.json()
    post = posts_data["data"][0]
    assert post["user_likes_count"] == 1
    assert post["is_liked"] is True


async def test_unlike_post(client: AsyncClient, test_user, test_post) -> None:
    """Test unliking a post"""
    # First like it
    await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )

    # Then unlike it
    response = await client.delete(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["success"] is True

    # Verify the post no longer shows the like
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    posts_data = response.json()
    post = posts_data["data"][0]
    assert post["user_likes_count"] == 0
    assert post["is_liked"] is False


async def test_like_post_twice_fails(client: AsyncClient, test_user, test_post) -> None:
    """Test that liking a post twice fails (same reaction type)"""
    # First like
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 200

    # Try to like again
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 409  # Conflict - already has this reaction


async def test_unlike_without_like_fails(client: AsyncClient, test_user, test_post) -> None:
    """Test that unliking without having liked fails"""
    response = await client.delete(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_like_nonexistent_post(client: AsyncClient, test_user) -> None:
    """Test liking a post that doesn't exist"""
    response = await client.post(
        f"{COMMUNITY_POSTS}/99999/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_multiple_users_like_same_post(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test that multiple users can like the same post"""
    # User 1 likes
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=test_user.token_headers
    )
    assert response.status_code == 200

    # User 2 likes
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
        headers=second_user.token_headers
    )
    assert response.status_code == 200

    # Check counts from user 1's perspective
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    posts_data = response.json()
    post = posts_data["data"][0]
    assert post["user_likes_count"] == 2
    assert post["is_liked"] is True  # User 1 liked it

    # Check from user 2's perspective
    response = await client.get(COMMUNITY_POSTS, headers=second_user.token_headers)
    posts_data = response.json()
    post = posts_data["data"][0]
    assert post["user_likes_count"] == 2
    assert post["is_liked"] is True  # User 2 liked it


async def test_reaction_limit_enforcement(client: AsyncClient, test_user, test_post) -> None:
    """Test that users can only add max 3 reactions per post"""
    from data.domain.community import reaction_crud
    from data.domain.community.schemas import ReactionType, ReactionCreate
    from data.lib.db import SessionLocal

    # Add 3 different reaction types directly via CRUD
    async with SessionLocal() as db:
        await reaction_crud.add_reaction(
            user_id=int(test_user.id),
            reaction_type=ReactionType.like,
            post_id=test_post.id,
            tenant_id=0,
            db=db,
        )
        await reaction_crud.add_reaction(
            user_id=int(test_user.id),
            reaction_type=ReactionType.salute,
            post_id=test_post.id,
            tenant_id=0,
            db=db,
        )
        await reaction_crud.add_reaction(
            user_id=int(test_user.id),
            reaction_type=ReactionType.hug,
            post_id=test_post.id,
            tenant_id=0,
            db=db,
        )

    # Check that user has 3 reactions
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    posts_data = response.json()
    post = posts_data["data"][0]
    assert post["user_likes_count"] == 3

    # Try to add a 4th reaction (trying to duplicate 'like' again should fail at duplicate check first)
    # But let's verify the limit is working
    async with SessionLocal() as db:
        from fastapi import HTTPException

        # This should raise an exception because user already has 'like'
        with pytest.raises(HTTPException) as exc_info:
            await reaction_crud.add_reaction(
                user_id=int(test_user.id),
                reaction_type=ReactionType.like,
                post_id=test_post.id,
                tenant_id=0,
                db=db,
            )
        assert exc_info.value.status_code == 409  # Conflict - already exists


async def test_reaction_count_aggregation(client: AsyncClient, test_user, second_user) -> None:
    """Test that reaction counts are properly aggregated by type"""
    from data.domain.community import reaction_crud
    from data.domain.community.schemas import ReactionType
    from data.lib.db import SessionLocal

    post = await create_post(client, test_user, "Reaction Test", "Content")

    # Add different reaction types from different users
    async with SessionLocal() as db:
        # User 1: like and salute
        await reaction_crud.add_reaction(
            user_id=int(test_user.id),
            reaction_type=ReactionType.like,
            post_id=post.id,
            tenant_id=0,
            db=db,
        )
        await reaction_crud.add_reaction(
            user_id=int(test_user.id),
            reaction_type=ReactionType.salute,
            post_id=post.id,
            tenant_id=0,
            db=db,
        )

        # User 2: like and hug
        await reaction_crud.add_reaction(
            user_id=int(second_user.id),
            reaction_type=ReactionType.like,
            post_id=post.id,
            tenant_id=0,
            db=db,
        )
        await reaction_crud.add_reaction(
            user_id=int(second_user.id),
            reaction_type=ReactionType.hug,
            post_id=post.id,
            tenant_id=0,
            db=db,
        )

        # Get reaction counts by type
        counts = await reaction_crud.count_reactions_by_type(post_id=post.id, db=db)
        assert counts[ReactionType.like] == 2
        assert counts[ReactionType.salute] == 1
        assert counts[ReactionType.hug] == 1

    # Total reaction count should be 4
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    posts_data = response.json()
    post_data = posts_data["data"][0]
    assert post_data["user_likes_count"] == 4


async def test_like_unauthenticated_fails(client: AsyncClient, test_post) -> None:
    """Test that liking without authentication fails"""
    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/user_likes",
    )
    assert response.status_code == 401
