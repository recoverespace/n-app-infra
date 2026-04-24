from sqladmin import ModelView
from sqlalchemy.sql.expression import Select, select
from starlette.requests import Request

from sqlalchemy import func
from admin.utils.jsonfield import JSONField
from data.domain.chats.models import Chat
from data.domain.users.models import User


class ChatAdmin(ModelView, model=Chat):
    name = "Chat"
    name_plural = "Chats"
    category = "Dialogs"
    category_icon = "fa-solid fa-comments"
    page_size = 25
    column_default_sort = [
        (Chat.created_at, True),
    ]
    form_overrides = dict(
        state=JSONField,
    )
    column_list = ["id", "user", "state", "created_at", "updated_at"]

    def list_query(self, request: Request) -> Select:
        return select(self.model).join(User).where(User.is_deleted is not True)

    column_searchable_list = (
        "id",
        "user_id",
    )

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0])).join(User).where(User.is_deleted is not True)

