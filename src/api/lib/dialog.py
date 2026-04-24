from api.lib.centrifuge import centrifuge
from api.v1.chats.schemas import CentrifugeMessageModel
from common.processing.schemas.dialog import DialogMessage, DialogResponseMessage, DialogActionMessage
from common.processing.streams import new_dialog_message
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.schemas.message import MessageActionType, ChatMessageCreate, ChatActionType
from data.domain.chat_messages.crud import chat_message_crud
from data.lib.db import SessionLocal
from common.otel import get_logger

logger = get_logger(__name__)


async def dialog_response(response: DialogResponseMessage):
    async with SessionLocal() as db:  # type: ignore
        messages = []
        message_id = 0
        for msg in response.items:
            if isinstance(msg, dict):
                msg["chat_id"] = response.chat_id
                msg["role"] = "assistant"
            else:
                msg.chat_id = response.chat_id
                msg.role = "assistant"
            message = ChatMessageCreate.model_validate(msg)
            if msg.role in ["assistant", "bot", "system"]:
                message.user_id = None
            message = await chat_message_crud.create(message, db=db)
            message_id = message.id
            messages.append(message)
        centrifuge_message = CentrifugeMessageModel(
            chat_id=response.chat_id,
            message_id=message_id,
            items=messages,
            action_type=MessageActionType.create,
        ).model_dump(mode="json")
        logger.info(f"Publishing centrifuge message: {centrifuge_message}")
        await centrifuge.publish(response.user_id, centrifuge_message)


async def dialog_typing(chat_id: int, user_id: int, is_typing: bool):
    await dialog_action(
        DialogActionMessage(
            user_id=user_id,
            chat_id=chat_id,
            action_type=ChatActionType.typing if is_typing else ChatActionType.not_typing,
        )
    )


async def dialog_action(response: DialogActionMessage):
    logger.info(f"Publishing centrifuge message: {response}")
    dump = response.model_dump(mode="json", exclude={"created_at", "updated_at"}, exclude_unset=True)
    for k in list(dump.keys()):
        if dump[k] is None:
            dump.pop(k)
    await centrifuge.publish(response.user_id, dump)


async def dialog_message(message: ChatMessage) -> DialogMessage:
    assert message.id is not None
    assert message.user_id is not None
    assert message.chat_id is not None

    msg = DialogMessage(
        user_id=message.user_id,
        chat_id=message.chat_id,
        message_id=message.id,
        items=[message.model_dump(mode="json")],
    )
    await new_dialog_message(msg)
    await centrifuge.publish(
        message.user_id,
        CentrifugeMessageModel(
            chat_id=message.chat_id,
            message_id=message.id,
            items=[message],
            action_type=MessageActionType.create,
        ).model_dump(mode="json"),
    )
    return msg


async def dialog_message_update(message: ChatMessage) -> DialogMessage:
    assert message.id is not None
    assert message.user_id is not None
    assert message.chat_id is not None

    msg = DialogMessage(
        user_id=message.user_id,
        chat_id=message.chat_id,
        message_id=message.id,
        items=[message.model_dump()],
    )
    await centrifuge.publish(
        message.user_id,
        CentrifugeMessageModel(
            chat_id=message.chat_id,
            message_id=message.id,
            items=[message],
            action_type=MessageActionType.update,
        ).model_dump(mode="json"),
    )
    return msg


async def dialog_message_delete(message: ChatMessage):
    await centrifuge.publish(
        message.user_id,
        CentrifugeMessageModel(chat_id=message.chat_id, message_id=message.id, action_type=MessageActionType.delete).model_dump(
            mode="json"
        ),
    )


async def dialog_message_ack(message: ChatMessage, user_id: int):
    await centrifuge.publish(
        user_id,
        CentrifugeMessageModel(chat_id=message.chat_id, message_id=message.id, action_type=MessageActionType.ack).model_dump(mode="json"),
    )
