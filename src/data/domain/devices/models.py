from sqlmodel import Relationship
from data.domain.devices.schemas import DeviceBase
from data.domain.users.models import User
from data.lib.model import BaseIDModel


class Device(BaseIDModel, DeviceBase, table=True):
    user: User = Relationship()
