from sqlmodel import Relationship
from data.domain.chats.schemas import ChatBase
from data.domain.users.models import User
from data.lib.model import BaseIDModel


class Chat(BaseIDModel, ChatBase, table=True):
    user: User = Relationship(sa_relationship_kwargs={"lazy": "joined"})

    def __str__(self) -> str:
        return f"[{self.id}]"
