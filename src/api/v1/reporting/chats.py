from fastapi import APIRouter, status, HTTPException, Depends
from sqlmodel import select, and_, col, or_, func
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from api.lib.deps import DBDep
from data.domain.chats.models import Chat
from data.domain.chats.schemas import ChatRead
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas.message import ChatMessageRead

from .schemas import ChatFilter, MessageFilter, PaginatedResponse

router = APIRouter()


async def build_chat_query(filters: ChatFilter, base_query):
    if filters.user_id:
        base_query = base_query.where(Chat.user_id == filters.user_id)

    # Date range filter
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

    return base_query


@router.get("/chats/", summary="List all chats")
async def list_chats(filters: ChatFilter = Depends(), db: AsyncSession = DBDep) -> PaginatedResponse:
    base_query = select(Chat)
    query = await build_chat_query(filters, base_query)

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    chats = (await db.exec(query)).all()

    return PaginatedResponse(
        items=[ChatRead.model_validate(chat).model_dump() for chat in chats],
        page=filters.page,
        size=filters.size,
    )


@router.get("/chats/{chat_id}", summary="Chat details")
async def get_chat(chat_id: int, db: AsyncSession = DBDep) -> ChatRead:
    chat = (await db.exec(select(Chat).where(Chat.id == chat_id))).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return ChatRead.model_validate(chat)


@router.get("/chats/{chat_id}/messages", summary="All messages in a chat")
async def get_chat_messages(
    chat_id: int, filters: MessageFilter = Depends(), db: AsyncSession = DBDep
) -> PaginatedResponse:
    # Check chat exists
    chat = (await db.exec(select(Chat).where(Chat.id == chat_id))).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")

    base_query = select(ChatMessage).where(ChatMessage.chat_id == chat_id)

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
