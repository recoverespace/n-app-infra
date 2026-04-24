"""Tests for content moderation (keyword filtering)"""
import pytest
from httpx import AsyncClient

from api.v1.community.tests.conftest import (
    COMMUNITY_POSTS,
    create_post,
    create_comment,
    add_blocked_keyword,
    test_user,
    test_post,
)


async def test_post_blocked_by_keyword(client: AsyncClient, test_user) -> None:
    """Test that posts containing blocked keywords are rejected"""
    # Add a blocked keyword
    await add_blocked_keyword("badword")

    payload = {
        "name": "Test Post",
        "body": "This contains a badword in the content",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }

    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400, response.text

    data = response.json()
    assert "badword" in data["detail"].lower()


async def test_comment_blocked_by_keyword(client: AsyncClient, test_user, test_post) -> None:
    """Test that comments containing blocked keywords are rejected"""
    # Add a blocked keyword
    await add_blocked_keyword("offensive")

    payload = {
        "comment": {
            "body": "This is an offensive comment",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 400, response.text

    data = response.json()
    assert "offensive" in data["detail"].lower()


async def test_keyword_case_insensitive(client: AsyncClient, test_user) -> None:
    """Test that keyword filtering is case-insensitive"""
    await add_blocked_keyword("spam")

    # Try with different cases
    payloads = [
        {"name": None, "body": "This is SPAM content"},
        {"name": None, "body": "This is Spam content"},
        {"name": None, "body": "This is spam content"},
    ]

    for payload in payloads:
        payload["is_comments_enabled"] = True
        payload["is_liking_enabled"] = True
        response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
        assert response.status_code == 400, f"Failed to block: {payload['body']}"


async def test_keyword_whole_word_matching(client: AsyncClient, test_user) -> None:
    """Test that keywords are matched as whole words"""
    await add_blocked_keyword("bad")

    # Should be blocked (whole word)
    payload = {
        "name": None,
        "body": "This is a bad post",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400

    # Should NOT be blocked (part of another word)
    payload = {
        "name": None,
        "body": "This is a badminton post",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201, response.text


async def test_multiple_keywords(client: AsyncClient, test_user) -> None:
    """Test blocking with multiple keywords"""
    await add_blocked_keyword("keyword1")
    await add_blocked_keyword("keyword2")
    await add_blocked_keyword("keyword3")

    # Block on first keyword
    payload = {
        "name": None,
        "body": "This has keyword1 in it",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400
    assert "keyword1" in response.json()["detail"].lower()

    # Block on second keyword
    payload["body"] = "This has keyword2 in it"
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400
    assert "keyword2" in response.json()["detail"].lower()

    # No blocked keywords - should succeed
    payload["body"] = "This has no blocked content"
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201


async def test_inactive_keyword_not_blocked(client: AsyncClient, test_user) -> None:
    """Test that inactive keywords don't block content"""
    from data.domain.community import blocked_keyword_crud
    from data.domain.community.schemas import BlockedKeywordCreate
    from data.lib.db import SessionLocal

    # Add an inactive keyword
    async with SessionLocal() as db:
        keyword_data = BlockedKeywordCreate(
            tenant_id=0,
            keyword="inactive",
            active=False,
        )
        await blocked_keyword_crud.create(keyword_data, db=db)

    # Should NOT be blocked (keyword is inactive)
    payload = {
        "name": None,
        "body": "This has inactive keyword in it",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201, response.text


async def test_moderation_log_created_on_keyword_block(client: AsyncClient, test_user) -> None:
    """Test that moderation logs are created when content is blocked"""
    from data.domain.community import moderation_log_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import ModerationLog

    await add_blocked_keyword("logged")

    payload = {
        "name": None,
        "body": "This has logged keyword",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400

    # Check that moderation log was created
    async with SessionLocal() as db:
        logs = await moderation_log_crud.get_multi(
            condition=col(ModerationLog.action) == "keyword_block",
            db=db
        )
        assert len(logs) > 0
        log = logs[0]
        assert "logged" in log.reason.lower()
        assert log.content_type == "post"


async def test_keyword_in_title_blocked(client: AsyncClient, test_user) -> None:
    """Test that keywords in post titles are also blocked"""
    await add_blocked_keyword("blocked")

    payload = {
        "name": "This title is blocked",
        "body": "Clean content",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 400


async def test_clean_content_passes(client: AsyncClient, test_user) -> None:
    """Test that content without blocked keywords passes"""
    await add_blocked_keyword("forbidden")

    payload = {
        "name": "Clean Title",
        "body": "This is perfectly fine content without any issues",
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=test_user.token_headers)
    assert response.status_code == 201, response.text


async def test_keyword_blocking_for_comments(client: AsyncClient, test_user, test_post) -> None:
    """Test keyword blocking specifically for comments"""
    await add_blocked_keyword("commentbad")

    payload = {
        "comment": {
            "body": "This comment is commentbad",
        }
    }

    response = await client.post(
        f"{COMMUNITY_POSTS}/{test_post.id}/comments",
        json=payload,
        headers=test_user.token_headers
    )
    assert response.status_code == 400

    # Verify moderation log
    from data.domain.community import moderation_log_crud
    from data.lib.db import SessionLocal
    from sqlmodel import col
    from data.domain.community.models import ModerationLog

    async with SessionLocal() as db:
        logs = await moderation_log_crud.get_multi(
            condition=col(ModerationLog.content_type) == "comment",
            db=db
        )
        assert len(logs) > 0
        assert logs[0].action == "keyword_block"
