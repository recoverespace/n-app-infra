import json
import random
from typing import AsyncGenerator
from uuid import uuid4
from enum import StrEnum
from common.otel import get_logger
from datetime import datetime, UTC
from data.domain.facts.schemas import UserFactCreate
from sqlmodel import all_, col
from asyncio import sleep
from data.lib.db import SessionLocal
from api.lib.dialog import dialog_typing, dialog_response, dialog_message_delete
from data.domain.chats import chat_crud, Chat
from data.domain.chat_messages import ChatMessage, chat_message_crud
from data.domain.intents.state import ChatState, ProactivityContext
from data.domain.chat_messages.schemas.message import Extra, ExtraAction, ExtraData, ExtraProactivity
from data.domain.chat_messages.schemas.suggestions import Suggestions, Suggestion
from data.domain.chat_messages.schemas.attachments import Attachment
from data.domain.facts import user_fact_crud, UserFact
from data.domain.users import user_crud, User


from common.processing.schemas.dialog import DialogResponseMessage

logger = get_logger(__name__)


class BaseDialog:
    def __init__(self, user_id: int, chat_id: int, value: str):
        self.user_id = user_id
        self.chat_id = chat_id
        self.value = value

    async def setup(self):
        pass

    async def change_dialog(self, dialog: str, value: str | None = None):
        # TODO: Implement dialog change
        raise NotImplementedError

    async def typing_delay():
        await sleep(random.randrange(10, 30) / 10.0)

    async def text(
        self,
        text: str,
        suggestions: list[Suggestion] | None = None,
        proactivity: ExtraProactivity | None = None,
        attachments: list[Attachment] | None = None,
        extra: Extra | None = None,
        as_user:bool=False
    ):
        suggestions = Suggestions(items=suggestions) if suggestions else None
        if not extra:
            extra = Extra(proactivity=proactivity) if proactivity else None
        elif proactivity:
            extra.proactivity = proactivity

        return ChatMessage(
            user_id=self.user_id if as_user else None,
            chat_id=self.chat_id,
            text=text,
            attachments=attachments,
            suggestions=suggestions,
            extra=extra,
        )

    async def attachment(self, attachment: Attachment):
        return ChatMessage(
            user_id=None,
            chat_id=self.chat_id,
            attachment=attachment,
        )

    async def messages(self) -> AsyncGenerator[ChatMessage | list[ChatMessage], None]:
        raise NotImplementedError

    async def dialog_typing(self, is_typing: bool):
        await dialog_typing(self.chat_id, self.user_id, is_typing=is_typing)

    async def process_message(self):
        await self.dialog_typing(is_typing=True)
        async for message_pack in self.messages():
            if not isinstance(message_pack, list):
                message_pack = [message_pack]
            for m in message_pack:
                await dialog_response(
                    DialogResponseMessage(
                        user_id=self.user_id, chat_id=self.chat_id, original_message_id=0, items=[m]
                    )
                )
            await self.typing_delay()
        await self.dialog_typing(is_typing=False)

    async def get_user(self) -> User:
        try:
            async with SessionLocal() as db:  # type: ignore
                user = await user_crud.get(col(User.id) == self.user_id, db=db)
                return user
        except Exception as e:
            logger.warning(f"Failed to get user {self.user_id} data: {str(e)}")

    async def update_settings(self, settings: dict):
        async with SessionLocal() as db:  # type: ignore
            user = await self.user
            new_settings = user.settings.model_copy(update=settings)
            await user_crud.update(user, {"settings": new_settings}, db=db)

    async def create_fact(self, kind: str, label: str, value: str) -> UserFact:
        async with SessionLocal() as db:  # type: ignore
            fact_date = datetime.now()
            return await user_fact_crud.create(
                UserFactCreate(
                    user_id=self.user_id,
                    kind=kind,
                    value=value,
                    label=label,
                    created_at=fact_date,
                ),
                db=db,
            )

    async def get_last_fact(self, kind: str) -> UserFact | None:
        try:
            async with SessionLocal() as db:  # type: ignore
                return await user_fact_crud.get_last_fact(user_id=self.user_id, kind=kind, db=db)
        except Exception as e:
            logger.warning(f"Failed to get user fact {self.user_id} data: {str(e)}")

    async def update_fact(self, fact: UserFact, update: dict):
        async with SessionLocal() as db:
            fact.value = update.get("value", fact.value)
            fact.label = update.get("label", fact.label)
            fact.extra = update.get("extra", fact.extra)
            await user_fact_crud.update(fact, fact.model_dump(), db=db)

    async def start_proactivity(self, kind: str, override_id: str | None = None) -> ExtraProactivity:
        proactivity_id = override_id or uuid4().hex
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == self.chat_id, db=db)
            await chat_crud.update(
                chat,
                {"state": ChatState(proactivity=ProactivityContext(id=proactivity_id, kind=kind))},
                db=db,
            )
        return ExtraProactivity(id=proactivity_id, kind=kind, state="start")

    async def chat_proactivity_id(self) -> str:
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == self.chat_id, db=db)
            return chat.state.proactivity.id
        return uuid4().hex

    async def get_last_proactivity(self) -> ExtraProactivity | None:
        try:
            async with SessionLocal() as db:  # type: ignore
                last_message = await chat_message_crud.get_last(
                    col(ChatMessage.chat_id) == self.chat_id, count=3, db=db
                )
                for message in last_message:
                    if message is not None and message.extra.proactivity is not None:
                        if message.extra.proactivity.state == "start":
                            return message.extra.proactivity
                            break

        except Exception as e:
            return None
