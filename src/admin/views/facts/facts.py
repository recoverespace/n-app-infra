from sqladmin import ModelView

from data.domain.facts import UserFact


class FactsAdmin(ModelView, model=UserFact):
    name = "Fact"
    name_plural = "Facts"
    category_icon = "fa-solid fa-magnifying-glass-chart"
    category = "App User Fact"
    page_size = 25
    column_default_sort = [
        (UserFact.created_at, True),
    ]
    column_list = ["id", "created_at", "user_id", "kind", "label", "value"]

    column_searchable_list = ["user_id", "kind"]
    column_sortable_list = (
        "user_id",
        "created_at",
    )
