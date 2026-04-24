from data.domain.devices.models import Device
from sqladmin import ModelView

from data.domain.users.models import User


class DeviceAdmin(ModelView, model=Device):
    name = "Device"
    name_plural = "Devices"
    category_icon = "fa-solid fa-mobile"
    category = "User Management"
    page_size = 25
    column_default_sort = [
        (Device.id, True),
    ]
    column_list = [
        "id",
        "user_id",
        "installed_at",
        "os",
        "platform",
        "device_model",
        "app_version",
        "timezone",
        "language",
    ]
    column_searchable_list = (
        "id",
        "user_id",
        "device_model",
    )
    column_sortable_list = (
        "id",
        "user_id",
        "installed_at",
        "os",
        "platform",
    )
    form_ajax_refs = {
        "user": {
            "fields": (User.id,),
            "order_by": User.updated_at,
        }
    }
