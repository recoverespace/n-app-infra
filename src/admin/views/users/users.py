import wtforms
from admin.utils.jsonfield import JSONField
from data.domain.users.models import User
from data.domain.chats import chat_crud
from data.domain.chat_messages import chat_message_crud
from data.domain.facts import user_fact_crud
from data.lib.db import SessionLocal
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func
from sqladmin import ModelView, action
from starlette.requests import Request
from starlette.responses import RedirectResponse


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    category_icon = "fa-solid fa-user"
    category = "User Management"
    page_size = 25
    column_default_sort = [
        (User.id, True),
    ]
    column_list = ["id", "uid", "first_name", "last_name", "email", "created_at", "is_active", "is_deleted"]
    column_searchable_list = (
        "id",
        "uid",
        "first_name",
        "last_name",
        "email",
    )
    column_sortable_list = (
        "id",
        "uid",
        "first_name",
        "last_name",
        "email",
        "created_at",
        "is_active",
    )
    form_overrides = dict(
        settings=JSONField,
        gifts=JSONField,
        email=wtforms.EmailField,
        avatar_url=wtforms.URLField,
    )
    form_widget_args = dict(
        uid={"readyonly": True},
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
    )

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0])).where(User.is_deleted != True)

    def list_query(self, request: Request) -> Select:
        return select(User).where(User.is_deleted != True)

    async def on_model_delete(self, model: User, request):
        async with SessionLocal() as db:
            chat = await chat_crud.get(condition=chat_crud.model.user_id == model.id, db=db)
            if chat:
                await chat_message_crud.remove_all(condition=chat_message_crud.model.chat_id == chat.id, db=db)
                await chat_crud.remove_all(condition=chat_crud.model.user_id == model.id, db=db)
            await user_fact_crud.remove_all(condition=user_fact_crud.model.user_id == model.id, db=db)
