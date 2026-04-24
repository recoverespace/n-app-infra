from sqlalchemy.sql.expression import Select, select
from starlette.requests import Request
from data.domain.chat_messages.models import ChatMessage, MessageFeedback
from sqladmin import ModelView

from data.domain.chats.models import Chat
from data.domain.users.models import User


class FeedbackAdmin(ModelView, model=MessageFeedback):
    name = "Feedback"
    name_plural = "Feedback"
    category_icon = "fa-solid fa-envelope"
    category = "Dialogs"
    page_size = 25
    column_default_sort = [
        (MessageFeedback.created_at, True),
    ]
    column_list = [
        "id",
        "chat",
        "user",
        "chat_message",
        "text",
        "updated_at",
    ]

    def list_query(self, request: Request) -> Select:
        return select(self.model).join(User).join(ChatMessage).join(Chat)

    # column_searchable_list = (
    #     Device.id,
    #     Device.user_id,
    #     Device.device_model,
    # )
    # column_sortable_list = (
    #     Device.id,
    #     Device.user_id,
    #     Device.installed_at,
    #     Device.os,
    #     Device.platform,
    # )
