from sqladmin import ModelView

from data.domain.config.models import Config


class ConfigAdmin(ModelView, model=Config):
    name = "Config"
    name_plural = "Configs"
    category_icon = "fa-solid fa-cogs"
    category = "App Configuration"
    page_size = 25
    column_default_sort = [
        (Config.created_at, True),
    ]
    column_list = ["id", "segment", "priority", "created_at", "updated_at"]

    column_searchable_list = ["segment"]
