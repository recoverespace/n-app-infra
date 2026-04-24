from sqladmin import ModelView, action
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func

from data.domain.community.models import UserBlock
from data.domain.community import user_block_crud, post_crud, comment_crud
from data.lib.db import SessionLocal


class UserBlockAdmin(ModelView, model=UserBlock):
    name = "User Block"
    name_plural = "Blocked Users"
    category_icon = "fa-solid fa-user-slash"
    category = "Community"
    page_size = 25

    column_default_sort = [
        (UserBlock.created_at, True),
    ]

    column_list = [
        "id",
        "user_id",
        "moderator_id",
        "reason",
        "created_at",
    ]

    column_searchable_list = (
        "reason",
    )

    column_sortable_list = (
        "id",
        "user_id",
        "moderator_id",
        "created_at",
    )

    column_details_list = [
        "id",
        "user",
        "moderator",
        "tenant_id",
        "reason",
        "created_at",
        "updated_at",
    ]

    form_widget_args = dict(
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
        tenant_id=dict(readonly=True),
    )

    form_excluded_columns = ["created_at", "updated_at"]

    can_create = True
    can_edit = True
    can_delete = True  # Unblock by deleting

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0]))

    def list_query(self, request: Request) -> Select:
        return select(UserBlock).order_by(UserBlock.created_at.desc())

    async def on_model_change(self, data: dict, model: UserBlock, is_created: bool, request: Request) -> None:
        """When a user is blocked, block all their content"""
        if is_created:
            async with SessionLocal() as db:
                # Block all user posts
                await post_crud.block_user_posts(model.user_id, model.tenant_id, db=db)
                # Block all user comments
                await comment_crud.block_user_comments(model.user_id, model.tenant_id, db=db)

    async def on_model_delete(self, model: UserBlock, request: Request) -> None:
        """When unblocking a user, optionally unblock their content"""
        # Note: For V1, we keep content blocked for safety
        # In V2, we could add an option to unblock content
        pass
