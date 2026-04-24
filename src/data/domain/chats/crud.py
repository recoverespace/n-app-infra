from datetime import datetime
from mimetypes import guess_type
from typing import IO
from urllib.parse import quote

from data.domain.chat_messages.schemas.attachments import AttachmentType, FileAttachment
from data.domain.chats.models import Chat
from data.domain.chats.schemas import ChatCreate, ChatUpdate
from data.lib.crud import CRUDBase
from data.settings import settings


class CRUDChat(CRUDBase[Chat, ChatCreate, ChatUpdate]):
    async def get_static_file(self, chat_id: int, filepath: str) -> FileAttachment:
        return FileAttachment(
            url=f"{settings.EXTERNAL_URL}/v1/chats/{chat_id}/media/static/{filepath}",  # noqa
            type=AttachmentType.file,
        )


chat_crud = CRUDChat(Chat)
