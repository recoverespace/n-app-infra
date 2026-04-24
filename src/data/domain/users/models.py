from sqlmodel import Relationship
from data.domain.users.schemas import UserBase
from data.domain.users.schemas import UserRefreshTokenBase
from data.lib.model import BaseIDModel


class User(BaseIDModel, UserBase, table=True):
    def __str__(self) -> str:
        name = self.display_name or " ".join([self.first_name or "", self.last_name or ""])
        if name == "":
            name = f"{self.id}"
        else:
            name = f"{self.id} {name}"
        return f"{name} ({self.email}) [{self.uid}]"


class UserRefreshToken(BaseIDModel, UserRefreshTokenBase, table=True):
    user: User = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
