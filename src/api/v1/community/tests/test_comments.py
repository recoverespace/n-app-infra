"""Tests for comment endpoints"""
import pytest
from httpx import AsyncClient

from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    create_post,
    create_comment,
    test_user,
    second_user,
    test_post,
    test_comment,
)


async def test_create_comment(client: AsyncClient, test_user, test_post) -> None:
    """Test creating a comment on a post"""
    payload = {
        "comment": {
            "body": "This is my comment",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["id"] is not None
    assert data["body_text"] == "This is my comment"
    assert data["post_id"] == test_post.id
    assert data["author"]["id"] == int(test_user.id)


async def test_create_comment_on_nonexistent_post(client: AsyncClient, test_user) -> None:
    """Test creating a comment on a post that doesn't exist"""
    payload = {
        "comment": {
            "body": "Comment on nothing",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/99999/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_create_comment_without_body(client: AsyncClient, test_user, test_post) -> None:
    """Test creating a comment without body fails"""
    payload = {
        "comment": {
            "body": "",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 400


async def test_create_comment_unauthenticated(client: AsyncClient, test_post) -> None:
    """Test creating a comment without authentication fails"""
    payload = {
        "comment": {
            "body": "Unauthorized comment",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
    )
    assert response.status_code == 401


async def test_get_comments_empty(client: AsyncClient, test_user, test_post) -> None:
    """Test getting comments when none exist"""
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert data["data"] == []
    assert data["meta"]["total"] == 0


async def test_get_comments_list(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test getting a list of comments"""
    # Create multiple comments
    await create_comment(client, test_user, test_post.id, "First comment")
    await create_comment(client, second_user, test_post.id, "Second comment")
    await create_comment(client, test_user, test_post.id, "Third comment")

    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 3
    assert data["meta"]["total"] == 3

    # Should be sorted by oldest first (ascending)
    assert data["data"][0]["body_text"] == "First comment"
    assert data["data"][1]["body_text"] == "Second comment"
    assert data["data"][2]["body_text"] == "Third comment"


async def test_get_comments_pagination(client: AsyncClient, test_user, test_post) -> None:
    """Test comment pagination"""
    # Create 5 comments
    for i in range(5):
        await create_comment(client, test_user, test_post.id, f"Comment {i+1}")

    # Get first page with 2 items
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        params={"page": 1, "per_page": 2},
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["total"] == 5
    assert data["meta"]["page"] == 1
    assert data["data"][0]["body_text"] == "Comment 1"
    assert data["data"][1]["body_text"] == "Comment 2"

    # Get second page
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        params={"page": 2, "per_page": 2},
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    assert len(data["data"]) == 2
    assert data["meta"]["page"] == 2
    assert data["data"][0]["body_text"] == "Comment 3"


async def test_get_comments_with_reactions(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test that comments include reaction counts"""
    comment = await create_comment(client, test_user, test_post.id, "Comment with reaction")

    # Add a like via reaction endpoint (would need to be implemented)
    # For now, we'll just check the structure
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    assert response.status_code == 200, response.text

    data = response.json()
    comment_data = data["data"][0]
    assert "user_likes_count" in comment_data
    assert "is_liked" in comment_data
    assert "replies_count" in comment_data


async def test_delete_own_comment(client: AsyncClient, test_user, test_post) -> None:
    """Test deleting own comment"""
    comment = await create_comment(client, test_user, test_post.id, "To delete")

    response = await client.delete(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments/{comment.id}",
        headers=test_user.token_headers
    )
    assert response.status_code == 204

    # Verify comment is deleted
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    data = response.json()
    assert len(data["data"]) == 0


async def test_delete_other_users_comment_fails(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test that user cannot delete another user's comment"""
    comment = await create_comment(client, test_user, test_post.id, "User 1 comment")

    # Try to delete as second user
    response = await client.delete(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments/{comment.id}",
        headers=second_user.token_headers
    )
    assert response.status_code == 403

    # Verify comment still exists
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    data = response.json()
    assert len(data["data"]) == 1


async def test_delete_nonexistent_comment(client: AsyncClient, test_user, test_post) -> None:
    """Test deleting a comment that doesn't exist"""
    response = await client.delete(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments/99999",
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_comments_exclude_blocked_content(client: AsyncClient, test_user, test_post) -> None:
    """Test that blocked comments are not shown in list"""
    from data.domain.community import comment_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import Comment

    # Create a comment
    comment = await create_comment(client, test_user, test_post.id, "Normal comment")

    # Block it via database
    async with SessionLocal() as db:
        db_comment = await comment_crud.get(col(Comment.id) == comment.id, db=db)
        await comment_crud.update(db_comment, {"blocked": True}, db=db)

    # Verify it's not in the list
    response = await client.get(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        headers=test_user.token_headers
    )
    data = response.json()
    assert len(data["data"]) == 0
    assert data["meta"]["total"] == 0


async def test_get_comments_on_nonexistent_post(client: AsyncClient, test_user) -> None:
    """Test getting comments on a post that doesn't exist"""
    response = await client.get(
        f"{COMMUNITY_POSTS}/99999/comments",
        headers=test_user.token_headers
    )
    assert response.status_code == 404
