from data.domain.static_files.schemas import StaticFileCreate, StaticFileUpdate
from data.domain.static_files.models import StaticFile

from data.lib.crud import CRUDBase


class CRUDDevice(CRUDBase[StaticFile, StaticFileCreate, StaticFileUpdate]): ...


static_file_crud = CRUDDevice(StaticFile)
