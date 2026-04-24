from collections.abc import Sequence
from datetime import timedelta
from fastapi import APIRouter, Request, status
from fastapi_pagination import Page
from opentelemetry import trace
from pydantic import TypeAdapter
from sqlmodel import and_, col

from api.lib.deps import ChatDep, DBDep, MessageDep, RedisDep, UserIDDep
from api.lib.dialog import (
    dialog_message,
    dialog_message_delete,
    dialog_message_update,
)
from data.domain.chat_messages.crud import chat_message_crud
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas import ChatMessageCreate, ChatMessageRead
from data.domain.chat_messages.schemas.message import MessageType
from common.otel import get_logger
from common.processing.streams import dialog_trigger
from common.processing.schemas.dialog import DialogTriggerMessage

router = APIRouter(prefix="/{chat_id}/messages")

tracer = trace.get_tracer(__name__)
logger = get_logger(__name__)


@router.get("/unacked")
async def get_unacked_messages() -> Sequence[ChatMessageRead]:
    messages = await chat_message_crud.get_unacked()
    return TypeAdapter(list[ChatMessageRead]).validate_python(messages)


@router.get("/")
async def get_chat_messages(chat=ChatDep, db=DBDep) -> Page[ChatMessageRead]:
    return await chat_message_crud.get_multi_paginated_ordered(
        order_by=[col(ChatMessage.created_at).desc()],
        condition=and_(
            ChatMessage.chat_id == chat.id,
            ChatMessage.message_type != MessageType.suggestion.value,
        ),
        db=db,
    )  # type: ignore


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def create_chat_message(data: ChatMessageCreate, chat=ChatDep, user_id=UserIDDep, db=DBDep) -> ChatMessageRead:
    data.chat_id = chat.id
    data.user_id = user_id
    data.role = "user"
    msg = await chat_message_crud.create(data, db=db)
    await dialog_message(msg)
    if msg.extra.selected_options and msg.extra.selected_options[0].value.startswith("trigger:"):
        kind = msg.extra.selected_options[0].value.replace("trigger:", "", 1)
        kind, value = kind.split(":") if ":" in kind else (kind, "")
        logger.info(f"Triggering {kind} with value {value}")
        await dialog_trigger(DialogTriggerMessage(user_id=user_id, chat_id=chat.id, kind=kind, extra={"value": value}))
    else:
        logger.info("No trigger found, sending message to chat service")
        await dialog_trigger(DialogTriggerMessage(user_id=user_id, chat_id=chat.id, kind="message", extra={"value": msg.text}))

    return ChatMessageRead.model_validate(msg)


@router.patch("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def update_chat_message(data: ChatMessageCreate, message=MessageDep, db=DBDep):
    updated = data.model_dump(exclude_unset=True, mode="json")
    msg: ChatMessage = await chat_message_crud.update(message, updated, db=db)
    await dialog_message_update(msg)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_message(message=MessageDep, user_id=UserIDDep, db=DBDep):
    _condition = and_(ChatMessage.id == message.id, ChatMessage.user_id == user_id)
    msg = await chat_message_crud.remove(_condition, db=db)
    await dialog_message_delete(msg)


@router.put("/", status_code=status.HTTP_204_NO_CONTENT)
async def trigger_chat_message(kind: str = "", value: str = "", chat=ChatDep, user_id=UserIDDep):
    if not chat or not chat.id or not kind:
        return
    logger.info("Triggering dialog")
    await dialog_trigger(DialogTriggerMessage(user_id=user_id, chat_id=chat.id, kind=kind, extra={"value": value}))
