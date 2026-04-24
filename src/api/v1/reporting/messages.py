from fastapi import APIRouter, Depends
from sqlmodel import select, func
from sqlmodel.ext.asyncio.session import AsyncSession

from api.lib.deps import DBDep
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas.message import ChatMessageRead

from .schemas import MessageFilter, PaginatedResponse

router = APIRouter()


async def build_message_query(filters: MessageFilter, base_query):
    if filters.user_id:
        base_query = base_query.where(ChatMessage.user_id == filters.user_id)
    if filters.chat_id:
        base_query = base_query.where(ChatMessage.chat_id == filters.chat_id)
    if filters.role:
        base_query = base_query.where(ChatMessage.role == filters.role)

    # Date range filter
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

    return base_query


@router.get("/messages/", summary="List all messages (searchable)")
async def list_messages(filters: MessageFilter = Depends(), db: AsyncSession = DBDep) -> PaginatedResponse:
    base_query = select(ChatMessage)
    query = await build_message_query(filters, base_query)

    # Apply pagination
    offset = (filters.page - 1) * filters.size
    query = query.offset(offset).limit(filters.size)

    messages = (await db.exec(query)).unique()

    return PaginatedResponse(
        items=[ChatMessageRead.model_validate(message).model_dump() for message in messages],
        page=filters.page,
        size=filters.size,
    )
