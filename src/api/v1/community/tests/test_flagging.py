"""Tests for content flagging functionality"""
import pytest
from httpx import AsyncClient

from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    COMMUNITY_FLAGGED,
    create_post,
    create_comment,
    test_user,
    second_user,
    test_post,
    test_comment,
)


async def test_flag_post(client: AsyncClient, test_user, second_user) -> None:
    """Test flagging a post for review"""
    post = await create_post(client, test_user, "Flaggable Post", "Content")

    payload = {
        "content_type": "post",
        "content_id": post.id,
        "reason": "Inappropriate content",
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=second_user.token_headers
    )
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["success"] is True


async def test_flag_comment(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test flagging a comment for review"""
    comment = await create_comment(client, test_user, test_post.id, "Flaggable comment")

    payload = {
        "content_type": "comment",
        "content_id": comment.id,
        "reason": "Spam",
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=second_user.token_headers
    )
    assert response.status_code == 201, response.text

    data = response.json()
    assert data["success"] is True


async def test_flag_nonexistent_post(client: AsyncClient, test_user) -> None:
    """Test flagging a post that doesn't exist"""
    payload = {
        "content_type": "post",
        "content_id": 99999,
        "reason": "Test",
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_flag_nonexistent_comment(client: AsyncClient, test_user) -> None:
    """Test flagging a comment that doesn't exist"""
    payload = {
        "content_type": "comment",
        "content_id": 99999,
        "reason": "Test",
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 404


async def test_flag_invalid_content_type(client: AsyncClient, test_user, test_post) -> None:
    """Test flagging with invalid content type"""
    payload = {
        "content_type": "invalid_type",
        "content_id": test_post.id,
        "reason": "Test",
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 400


async def test_flag_creates_moderation_log(client: AsyncClient, test_user, second_user) -> None:
    """Test that flagging creates a moderation log entry"""
    from data.domain.community import moderation_log_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import ModerationLog

    post = await create_post(client, test_user, "Post to flag", "Content")

    reason = "Contains misinformation"
    payload = {
        "content_type": "post",
        "content_id": post.id,
        "reason": reason,
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=second_user.token_headers
    )
    assert response.status_code == 201

    # Verify moderation log was created
    async with SessionLocal() as db:
        logs = await moderation_log_crud.get_multi(
            condition=col(ModerationLog.action) == "content_flag",
            db=db
        )
        assert len(logs) > 0

        # Find the log for this specific flag
        flag_log = None
        for log in logs:
            if log.content_id == post.id and log.content_type == "post":
                flag_log = log
                break

        assert flag_log is not None
        assert flag_log.reason == reason
        assert flag_log.moderator_id == int(second_user.id)  # User who flagged
        assert flag_log.content_type == "post"
        assert flag_log.content_id == post.id


async def test_flag_own_content(client: AsyncClient, test_user, test_post) -> None:
    """Test that users can flag their own content (edge case)"""
    payload = {
        "content_type": "post",
        "content_id": test_post.id,
        "reason": "I want to report my own post",
    }

    # This should technically work (no restriction on flagging own content)
    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 201


async def test_flag_unauthenticated(client: AsyncClient, test_post) -> None:
    """Test that unauthenticated users cannot flag content"""
    payload = {
        "content_type": "post",
        "content_id": test_post.id,
        "reason": "Test",
    }

    response = await client.post(COMMUNITY_FLAGGED, json=payload)
    assert response.status_code == 401


async def test_multiple_flags_on_same_content(client: AsyncClient, test_user, second_user) -> None:
    """Test that multiple users can flag the same content"""
    from api.lib.tests.utils import init_user

    post = await create_post(client, test_user, "Controversial Post", "Content")

    # First user flags
    payload = {
        "content_type": "post",
        "content_id": post.id,
        "reason": "Offensive",
    }
    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=second_user.token_headers
    )
    assert response.status_code == 201

    # Third user also flags
    third_user = await init_user(client)
    payload["reason"] = "Spam"
    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=third_user.token_headers
    )
    assert response.status_code == 201

    # Both flags should be recorded
    from data.domain.community import moderation_log_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col, and_
    from data.domain.community.models import ModerationLog

    async with SessionLocal() as db:
        logs = await moderation_log_crud.get_multi(
            condition=and_(
                col(ModerationLog.action) == "content_flag",
                col(ModerationLog.content_id) == post.id,
                col(ModerationLog.content_type) == "post",
            ),
            db=db
        )
        assert len(logs) >= 2  # At least the two we just created


async def test_flag_comment_with_detailed_reason(client: AsyncClient, test_user, second_user, test_post) -> None:
    """Test flagging with a detailed reason"""
    comment = await create_comment(client, test_user, test_post.id, "Problematic comment")

    detailed_reason = "This comment violates community guidelines by containing hate speech and personal attacks"

    payload = {
        "content_type": "comment",
        "content_id": comment.id,
        "reason": detailed_reason,
    }

    response = await client.post(
        COMMUNITY_FLAGGED,
        json=payload,
        headers=second_user.token_headers
    )
    assert response.status_code == 201

    # Verify the detailed reason was stored
    from data.domain.community import moderation_log_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col, and_
    from data.domain.community.models import ModerationLog

    async with SessionLocal() as db:
        log = await moderation_log_crud.get(
            condition=and_(
                col(ModerationLog.action) == "content_flag",
                col(ModerationLog.content_id) == comment.id,
                col(ModerationLog.content_type) == "comment",
            ),
            db=db
        )
        assert log is not None
        assert log.reason == detailed_reason
