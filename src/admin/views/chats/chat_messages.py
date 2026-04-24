from admin.utils.jsonfield import JSONField
from data.domain.chat_messages.models import ChatMessage, MessageReaction
from sqladmin import ModelView


class ChatMessageAdmin(ModelView, model=ChatMessage):
    name = "Message"
    name_plural = "Messages"
    category_icon = "fa-solid fa-comment"
    category = "Dialogs"
    page_size = 25
    column_default_sort = [
        (ChatMessage.created_at, True),
    ]
    column_list = [
        "id",
        "chat",
        "user_id",
        "role",
        "text",
        "message_type",
        "acked_at",
        "updated_at",
    ]
    column_searchable_list = (
        "id",
        "uid",
        "chat_id",
        "user_id",
        "text",
        "acked_at",
    )

    form_overrides = dict(
        notification=JSONField,
        suggestions=JSONField,
        extra=JSONField,
    )
    form_ajax_refs = {
        "reactions": {
            "fields": (MessageReaction.chat_message_id,),
            "order_by": MessageReaction.id,
        }
    }
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
