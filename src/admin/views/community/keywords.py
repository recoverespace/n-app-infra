from sqladmin import ModelView
from starlette.requests import Request
from sqlalchemy.sql.expression import Select, select
from sqlalchemy import func

from data.domain.community.models import BlockedKeyword


class BlockedKeywordAdmin(ModelView, model=BlockedKeyword):
    name = "Blocked Keyword"
    name_plural = "Blocked Keywords"
    category_icon = "fa-solid fa-ban"
    category = "Community"
    page_size = 50

    column_default_sort = [
        (BlockedKeyword.keyword, False),
    ]

    column_list = [
        "id",
        "keyword",
        "active",
        "tenant_id",
        "created_at",
    ]

    column_searchable_list = (
        "keyword",
    )

    column_sortable_list = (
        "id",
        "keyword",
        "active",
        "created_at",
    )

    column_details_list = [
        "id",
        "tenant_id",
        "keyword",
        "active",
        "created_at",
        "updated_at",
    ]

    form_widget_args = dict(
        created_at=dict(readonly=True),
        updated_at=dict(readonly=True),
    )

    form_excluded_columns = ["created_at", "updated_at"]

    can_create = True
    can_edit = True
    can_delete = True

    def count_query(self, request: Request) -> Select:
        return select(func.count(self.pk_columns[0]))

    def list_query(self, request: Request) -> Select:
        return select(BlockedKeyword).order_by(BlockedKeyword.keyword)
