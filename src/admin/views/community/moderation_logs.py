from sqladmin import ModelView
from starlette.requests import Request
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func

from data.domain.community.models import ModerationLog


class ModerationLogAdmin(ModelView, model=ModerationLog):
    name = "Moderation Log"
    name_plural = "Moderation Logs"
    category_icon = "fa-solid fa-clipboard-list"
    category = "Community"
    page_size = 50

    column_default_sort = [
        (ModerationLog.created_at, True),  # Latest first
    ]

    column_list = [
        "id",
        "action",
        "content_type",
        "content_id",
        "moderator_id",
        "reason",
        "created_at",
    ]

    column_searchable_list = (
        "reason",
        "metadata",
    )

    column_sortable_list = (
        "id",
        "action",
        "content_type",
        "content_id",
        "moderator_id",
        "created_at",
    )

    column_details_list = [
        "id",
        "tenant_id",
        "action",
        "content_type",
        "content_id",
        "moderator",
        "reason",
        "metadata",
        "created_at",
        "updated_at",
    ]

    form_widget_args = dict(
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
    )

    # Read-only view for audit trail
    can_create = False
    can_edit = False
    can_delete = False

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0]))

    def list_query(self, request: Request) -> Select:
        return select(ModerationLog).order_by(ModerationLog.created_at.desc())
