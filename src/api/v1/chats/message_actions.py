from datetime import datetime
from fastapi import APIRouter, status
from sqlmodel import and_, col
from api.lib.deps import UserIDDep, DBDep, MessageDep
from api.lib.dialog import dialog_message_ack, dialog_message_update
from api.v1.chats.schemas import ChatMessageAckModel
from data.domain.chat_messages.crud import chat_message_crud, message_reaction_crud, message_feedback_crud
from data.domain.chat_messages.schemas.feedback import MessageFeedbackCreate
from data.domain.chat_messages.schemas.reaction import MessageReactionCreate
from data.domain.chat_messages.models import ChatMessage, MessageReaction
from opentelemetry import trace

router = APIRouter(prefix="/{chat_id}/messages")

tracer = trace.get_tracer(__name__)


@router.post("/{message_id}/ack", status_code=status.HTTP_204_NO_CONTENT)
async def ack_chat_message(
    data: ChatMessageAckModel | None = None, message=MessageDep, user_id=UserIDDep, db=DBDep
):
    with tracer.start_as_current_span(
        "message_ack",
        attributes={
            "message_id": message.id or -1,
            "chat_id": message.chat_id or -1,
            "user_id": user_id or -1,
        },
    ):
        if not data:
            data = ChatMessageAckModel(acked_at=datetime.now())
        msg: ChatMessage = await chat_message_crud.update(message, data.model_dump(), db=db)
        await dialog_message_ack(msg, user_id)


@router.post("/{message_id}/reactions/", status_code=status.HTTP_201_CREATED)
async def create_reaction(data: MessageReactionCreate, message=MessageDep, user_id=UserIDDep, db=DBDep):
    with tracer.start_as_current_span(
        "message_reaction",
        attributes={
            "message_id": message.id or -1,
            "chat_id": message.chat_id or -1,
            "user_id": user_id or -1,
            "type": data.reaction_type.value,
        },
    ):
        assert message.id is not None
        assert message.chat_id is not None
        data.user_id = user_id
        data.chat_id = message.chat_id
        data.chat_message_id = message.id
        await message_reaction_crud.create(data, db=db)
        msg = await chat_message_crud.get(col(ChatMessage.id) == message.id, db=db)
        assert msg is not None
        await dialog_message_update(msg)


@router.delete("/{message_id}/reactions/{reaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reaction(reaction_id: int, message=MessageDep, user_id=UserIDDep, db=DBDep):
    with tracer.start_as_current_span(
        "message_reaction_delete",
        attributes={
            "message_id": message.id or -1,
            "chat_id": message.chat_id or -1,
            "user_id": user_id or -1,
        },
    ):
        _reaction_condition = and_(
            MessageReaction.id == reaction_id,
            MessageReaction.user_id == user_id,
            MessageReaction.chat_message_id == message.id,
        )
        await message_reaction_crud.remove(_reaction_condition, db=db)
        msg = await chat_message_crud.get(col(ChatMessage.id) == message.id, db=db)
        assert msg is not None
        await dialog_message_update(msg)


@router.post("/{message_id}/feedbacks/", status_code=status.HTTP_201_CREATED)
async def create_feedback(data: MessageFeedbackCreate, message=MessageDep, user_id=UserIDDep, db=DBDep):
    with tracer.start_as_current_span(
        "message_feedback",
        attributes={
            "message_id": message.id or -1,
            "chat_id": message.chat_id or -1,
            "user_id": user_id or -1,
        },
    ):
        assert message.id is not None
        assert message.chat_id is not None
        data.user_id = user_id
        data.chat_id = message.chat_id
        data.chat_message_id = message.id
        await message_feedback_crud.create(data, db=db)
