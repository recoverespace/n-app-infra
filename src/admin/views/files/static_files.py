from sqladmin import ModelView

from data.domain.static_files.models import StaticFile


class StaticFileAdmin(ModelView, model=StaticFile):
    name = "Static File"
    name_plural = "Static Files"
    category_icon = "fa-solid fa-file"
    category = "Files"
    page_size = 25
    column_default_sort = [
        (StaticFile.created_at, True),
    ]
    column_list = [
        "id",
        "group",
        "path",
        "content_type",
        "updated_at",
    ]

    column_searchable_list = [StaticFile.group, StaticFile.path]
