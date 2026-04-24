from data.domain.devices.schemas import DeviceCreate, DeviceUpdate
from data.domain.devices.models import Device

from data.lib.crud import CRUDBase


class CRUDDevice(CRUDBase[Device, DeviceCreate, DeviceUpdate]): ...


device_crud = CRUDDevice(Device)
