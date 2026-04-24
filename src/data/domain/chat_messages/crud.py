from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlmodel import and_, select, col
from sqlmodel.ext.asyncio.session import AsyncSession

from data.domain.chat_messages.models import ChatMessage, MessageFeedback, MessageReaction
from data.domain.chat_messages.schemas import ChatMessageCreate, ChatMessageUpdate
from data.domain.chat_messages.schemas.feedback import MessageFeedbackCreate, MessageFeedbackUpdate
from data.domain.chat_messages.schemas.reaction import MessageReactionCreate, MessageReactionUpdate
from data.domain.users.models import User
from data.lib.crud import CRUDBase


class CRUDChatMessage(CRUDBase[ChatMessage, ChatMessageCreate, ChatMessageUpdate]):
    async def get_unacked(
        self, *, max_time: int = 3600, count: int = 1000, db: AsyncSession | None = None
    ) -> Sequence[ChatMessage]:
        scheduled_time = datetime.now()
        cutoff_time = scheduled_time - timedelta(seconds=max_time)
        session = self.get_db(db)
        query = (
            select(self.model)
            .join(User, col(self.model.user_id) == User.id, isouter=True)
            .where(
                and_(
                    col(ChatMessage.acked_at) is None,
                    col(ChatMessage.scheduled_at) < scheduled_time,
                    col(ChatMessage.notification) is not None,
                    col(ChatMessage.notification)["sent_at"] is None,
                    col(ChatMessage.created_at) > cutoff_time,
                    col(ChatMessage.user_id) is None,
                    col(User.settings)["notifications_enabled"].astext.cast(bool) is True,
                )
            )
            .limit(count)
        )
        response = await session.exec(query)
        return response.all()


class CRUDMessageReaction(CRUDBase[MessageReaction, MessageReactionCreate, MessageReactionUpdate]): ...


class CRUDMessageFeedback(CRUDBase[MessageFeedback, MessageFeedbackCreate, MessageFeedbackUpdate]): ...


chat_message_crud = CRUDChatMessage(ChatMessage)
message_reaction_crud = CRUDMessageReaction(MessageReaction)
message_feedback_crud = CRUDMessageFeedback(MessageFeedback)
