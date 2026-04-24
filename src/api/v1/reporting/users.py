from fastapi import APIRouter, status, HTTPException, Depends, Query
from sqlmodel import select, and_, col, or_, func, text
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from api.lib.deps import DBDep
from data.domain.users.models import User
from data.domain.users.schemas import UserRead
from data.domain.facts.models import UserFact
from data.domain.facts.schemas import UserFactRead
from data.domain.chats.models import Chat
from data.domain.chats.schemas import ChatRead
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas.message import ChatMessageRead

from .schemas import UserFilter, FactFilter, ChatFilter, MessageFilter, PaginatedResponse

router = APIRouter()


async def build_user_query(filters: UserFilter, base_query):
    if filters.user_id:
        base_query = base_query.where(User.id == filters.user_id)
    if filters.email:
        base_query = base_query.where(User.email.contains(filters.email))
    if filters.first_name:
        base_query = base_query.where(User.first_name.contains(filters.first_name))
    if filters.last_name:
        base_query = base_query.where(User.last_name.contains(filters.last_name))
    if filters.display_name:
        base_query = base_query.where(User.display_name.contains(filters.display_name))
    if filters.is_active is not None:
        base_query = base_query.where(User.is_active == filters.is_active)
    if filters.is_deleted is not None:
        base_query = base_query.where(User.is_deleted == filters.is_deleted)

    # Settings-based filters
    if filters.is_onboarding_finished is not None:
        base_query = base_query.where(
            text(f"\"user\".settings ->> 'is_onboarding_finished' ilike '{filters.is_onboarding_finished}'")
        )
    if filters.notifications_enabled is not None:
        base_query = base_query.where(
            text(f"\"user\".settings ->> 'notifications_enabled' ilike '{filters.notifications_enabled}'")
        )
    if filters.is_migrated_user is not None:
        base_query = base_query.where(
            text(f"\"user\".settings ->> 'is_migrated_user' ilike '{filters.is_migrated_user}'")
        )
    if filters.source:
        base_query = base_query.where(text(f"\"user\".settings ->> 'user_source' ilike '{filters.source}'"))

    # Date range filter
    if filters.start_date:
        base_query = base_query.where(User.created_at >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(User.created_at <= filters.end_date)

    # Sorting
    if filters.sort_by:
        sort_column = getattr(User, filters.sort_by, None)
        if sort_column:
            if filters.sort_order == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(User.created_at.desc())

    return base_query


@router.get("/users/", summary="List all users")
async def list_users(filters: UserFilter = Depends(), db: AsyncSession = DBDep) -> PaginatedResponse:
    base_query = select(User)
    query = await build_user_query(filters, base_query)

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    users = (await db.exec(query)).all()

    return PaginatedResponse(
        items=[UserRead.model_validate(user).model_dump() for user in users],
        page=filters.page,
        size=filters.size,
    )


@router.get("/users/{user_id}", summary="Get user profile")
async def get_user(user_id: int, db: AsyncSession = DBDep) -> UserRead:
    user = (await db.exec(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.get("/users/{user_id}/facts/", summary="Get all facts for a user")
async def get_user_facts(
    user_id: int, filters: FactFilter = Depends(), db: AsyncSession = DBDep
) -> PaginatedResponse:
    # Check user exists
    user = (await db.exec(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    base_query = select(UserFact).where(UserFact.user_id == user_id)

    if filters.kind:
        base_query = base_query.where(UserFact.kind.contains(filters.kind))
    if filters.start_date:
        base_query = base_query.where(UserFact.created_at >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(UserFact.created_at <= filters.end_date)

    # Sorting
    if filters.sort_by:
        sort_column = getattr(UserFact, filters.sort_by, None)
        if sort_column:
            if filters.sort_order == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(UserFact.created_at.desc())

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    base_query = base_query.offset(offset).limit(filters.size)

    facts = (await db.exec(base_query)).all()

    return PaginatedResponse(
        items=[UserFactRead.model_validate(fact).model_dump() for fact in facts],
        page=filters.page,
        size=filters.size,
    )


@router.get("/users/{user_id}/chats/", summary="Get all chats for a user")
async def get_user_chats(
    user_id: int, filters: ChatFilter = Depends(), db: AsyncSession = DBDep
) -> PaginatedResponse:
    # Check user exists
    user = (await db.exec(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    base_query = select(Chat).where(Chat.user_id == user_id)

    if filters.start_date:
        base_query = base_query.where(Chat.created_at >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(Chat.created_at <= filters.end_date)

    # Sorting
    if filters.sort_by:
        sort_column = getattr(Chat, filters.sort_by, None)
        if sort_column:
            if filters.sort_order == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(Chat.created_at.desc())

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    base_query = base_query.offset(offset).limit(filters.size)

    chats = (await db.exec(base_query)).all()

    return PaginatedResponse(
        items=[ChatRead.model_validate(chat).model_dump() for chat in chats],
        page=filters.page,
        size=filters.size,
    )


@router.get("/users/{user_id}/messages", summary="All user messages")
async def get_user_messages(
    user_id: int, filters: MessageFilter = Depends(), db: AsyncSession = DBDep
) -> PaginatedResponse:
    # Check user exists
    user = (await db.exec(select(User).where(User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # For user messages, first get appropriate chat for user, then filter messages by chat_id
    user_chats = list((await db.exec(select(Chat.id).where(Chat.user_id == user_id))).all())
    if not user_chats:
        return PaginatedResponse(items=[], page=filters.page, size=filters.size, total=0, total_pages=0)

    base_query = select(ChatMessage).where(ChatMessage.chat_id.in_(user_chats))

    if filters.start_date:
        base_query = base_query.where(ChatMessage.created_at >= filters.start_date)
    if filters.end_date:
        base_query = base_query.where(ChatMessage.created_at <= filters.end_date)

    # Sorting
    if filters.sort_by:
        sort_column = getattr(ChatMessage, filters.sort_by, None)
        if sort_column:
            if filters.sort_order == "desc":
                base_query = base_query.order_by(sort_column.desc())
            else:
                base_query = base_query.order_by(sort_column)
    else:
        base_query = base_query.order_by(ChatMessage.created_at.desc())

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    base_query = base_query.offset(offset).limit(filters.size)

    messages = (await db.exec(base_query)).unique()

    return PaginatedResponse(
        items=[ChatMessageRead.model_validate(message).model_dump() for message in messages],
        page=filters.page,
        size=filters.size,
    )
