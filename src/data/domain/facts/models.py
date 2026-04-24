from sqlmodel import Relationship
from data.domain.facts.schemas import UserFactBase
from data.domain.users.models import User
from data.lib.model import BaseIDModel


class UserFact(BaseIDModel, UserFactBase, table=True):
    user: User = Relationship()
