from data.domain.static_files.schemas import StaticFileBase
from data.lib.model import BaseIDModel


class StaticFile(BaseIDModel, StaticFileBase, table=True): ...
