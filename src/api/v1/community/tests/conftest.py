"""Test fixtures for community tests"""
import pytest
from httpx import AsyncClient
from dataclasses import dataclass

from api.lib.tests.utils import init_user, NewUser
from data.domain.community import post_crud, comment_crud, blocked_keyword_crud, user_block_crud
from data.domain.community.schemas import PostCreate, CommentCreate, BlockedKeywordCreate
from data.lib.db import SessionLocal


COMMUNITY_POSTS = "/v1/community/posts"
COMMUNITY_FLAGGED = "/v1/community/flagged_contents"


@dataclass
class NewPost:
    id: int
    title: str | None
    content: str
    user: NewUser


@dataclass
class NewComment:
    id: int
    post_id: int
    content: str
    user: NewUser


async def create_post(
    client: AsyncClient,
    user: NewUser,
    title: str | None = None,
    content: str = "Test post content"
) -> NewPost:
    """Helper to create a post"""
    payload = {
        "name": title,
        "body": content,
        "is_comments_enabled": True,
        "is_liking_enabled": True,
    }
    response = await client.post(COMMUNITY_POSTS, json=payload, headers=user.token_headers)
    assert response.status_code == 201, response.text
    data = response.json()
    return NewPost(
        id=data["id"],
        title=data["name"],
        content=data["body"],
        user=user,
    )


async def create_comment(
    client: AsyncClient,
    user: NewUser,
    post_id: int,
    content: str = "Test comment content"
) -> NewComment:
    """Helper to create a comment"""
    payload = {
        "comment": {
            "body": content,
        }
    }
    response = await client.post(
        f"{COMMUNITY_POSTS}/{post_id}/comments",
        json=payload,
        headers=user.token_headers
    )
    assert response.status_code == 201, response.text
    data = response.json()
    return NewComment(
        id=data["id"],
        post_id=post_id,
        content=data["body_text"],
        user=user,
    )


async def add_blocked_keyword(keyword: str, tenant_id: int = 0) -> None:
    """Helper to add a blocked keyword"""
    async with SessionLocal() as db:
        keyword_data = BlockedKeywordCreate(
            tenant_id=tenant_id,
            keyword=keyword,
            active=True,
        )
        await blocked_keyword_crud.create(keyword_data, db=db)


async def block_user(user_id: int, moderator_id: int, reason: str = "Test block", tenant_id: int = 0) -> None:
    """Helper to block a user"""
    async with SessionLocal() as db:
        await user_block_crud.block_user(
            user_id=user_id,
            reason=reason,
            moderator_id=moderator_id,
            tenant_id=tenant_id,
            db=db,
        )


@pytest.fixture
async def test_user(client: AsyncClient) -> NewUser:
    """Create a test user"""
    return await init_user(client)


@pytest.fixture
async def second_user(client: AsyncClient) -> NewUser:
    """Create a second test user"""
    return await init_user(client)


@pytest.fixture
async def test_post(client: AsyncClient, test_user: NewUser) -> NewPost:
    """Create a test post"""
    return await create_post(client, test_user, title="Test Post", content="This is a test post")


@pytest.fixture
async def test_comment(client: AsyncClient, test_user: NewUser, test_post: NewPost) -> NewComment:
    """Create a test comment"""
    return await create_comment(client, test_user, test_post.id, "This is a test comment")
