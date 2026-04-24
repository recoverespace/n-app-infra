"""Tests for post endpoints"""
import pytest
from httpx import AsyncClient

from api.lib.tests.utils import init_user
from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    create_post,
    test_user,
    second_user,
    test_post,
)


async def test_create_post(client: AsyncClient, test_user) -> None:
    """Test creating a post"""
    payload = {
        "name": "My First Post",
        "body": "This is the content of my post",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }

    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["id"] is not None
    assert data["name"] == "My First Post"
    assert data["body"] == "This is the content of my post"
    assert data["author"]["id"] == int(test_user.id)


async def test_create_post_without_title(client: AsyncClient, test_user) -> None:
    """Test creating a post without a title (title is optional)"""
    payload = {
        "name": None,
        "body": "Content without title",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }

    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["id"] is not None
    assert data["name"] is None
    assert data["body"] == "Content without title"


async def test_create_post_unauthenticated(client: AsyncClient) -> None:
    """Test creating a post without authentication fails"""
    payload = {
        "name": "Test",
        "body": "Content",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }

    response = await client.post(COMMUNITY_POSTS, json=payload)
    assert response.status_code == 401


async def test_get_posts_empty(client: AsyncClient, test_user) -> None:
    """Test getting posts when none exist"""
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0
    assert data["meta"]["page"] == 1


async def test_get_posts_list(client: AsyncClient, test_user) -> None:
    """Test getting a list of posts"""
    # Create multiple posts
    await create_post(client, test_user, "Post 1", "Content 1")
    await create_post(client, test_user, "Post 2", "Content 2")
    await create_post(client, test_user, "Post 3", "Content 3")

    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 3
    assert data["meta"]["total"] == 3

    # Should be sorted by latest first
    assert data["data"][0]["name"] == "Post 3"
    assert data["data"][1]["name"] == "Post 2"
    assert data["data"][2]["name"] == "Post 1"


async def test_get_posts_pagination(client: AsyncClient, test_user) -> None:
    """Test post pagination"""
    # Create 5 posts
    for i in range(5):
        await create_post(client, test_user, f"Post {i+1}", f"Content {i+1}")

    # Get first page with 2 items
    response = await client.get(
        COMMUNITY_POSTS,
        params={"page": 1, "per_page": 2},
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 5
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 2

    # Get second page
    response = await client.get(
        COMMUNITY_POSTS,
        params={"page": 2, "per_page": 2},
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 2


async def test_get_posts_with_reactions_and_comments(client: AsyncClient, test_user, second_user) -> None:
    """Test that posts include reaction counts and comment counts"""
    post = await create_post(client, test_user, "Test Post", "Content")

    # Add a comment
    comment_payload = {"comment": {"body": "Nice post!"}}
    await client.post(
        f"{COMMUNITY_POSTS}/{post.id}/comments",
        json=comment_payload,
        headers=second_user.token_headers
    )

    # Add a like
    await client.post(
        f"{COMMUNITY_POSTS}/{post.id}/user_likes",
        headers=second_user.token_headers
    )

    # Get posts list
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    assert response.status_code == 200, response.text

    data = response.json()
    post_data = data["data"][0]
    assert post_data["comment_count"] == 1
    assert post_data["user_likes_count"] == 1
    assert post_data["is_liked"] is False  # test_user didn't like it

    # Check from second user's perspective
    response = await client.get(COMMUNITY_POSTS, headers=second_user.token_headers)
    data = response.json()
    post_data = data["data"][0]
    assert post_data["is_liked"] is True  # second_user liked it


async def test_delete_own_post(client: AsyncClient, test_user) -> None:
    """Test deleting own post"""
    post = await create_post(client, test_user, "To Delete", "Content")

    response = await client.delete(
        f"{COMMUNITY_POSTS}/{post.id}",
        headers=test_user.token_headers
    )
    assert response.status_code == 204

    # Verify post is deleted
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 0


async def test_delete_other_users_post_fails(client: AsyncClient, test_user, second_user) -> None:
    """Test that user cannot delete another user's post"""
    post = await create_post(client, test_user, "User 1 Post", "Content")

    # Try to delete as second user
    response = await client.delete(
        f"{COMMUNITY_POSTS}/{post.id}",
        headers=second_user.token_headers
    )
    assert response.status_code == 403

    # Verify post still exists
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 1


async def test_delete_nonexistent_post(client: AsyncClient, test_user) -> None:
    """Test deleting a post that doesn't exist"""
    response = await client.delete(
        f"{COMMUNITY_POSTS}/99999",
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_posts_exclude_blocked_content(client: AsyncClient, test_user) -> None:
    """Test that blocked posts are not shown in list"""
    from data.domain.community import post_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import Post

    # Create a post
    post = await create_post(client, test_user, "Normal Post", "Content")

    # Block it via database
    async with SessionLocal() as db:
        db_post = await post_crud.get(col(Post.id) == post.id, db=db)
        await post_crud.update(db_post, {"blocked": True}, db=db)

    # Verify it's not in the list
    response = await client.get(COMMUNITY_POSTS, headers=test_user.token_headers)
    data = response.json()
    assert len(data["data"]) == 0
    assert data["meta"]["total"] == 0
