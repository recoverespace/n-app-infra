from data.domain.config.schemas import ConfigBase
from data.lib.model import BaseIDModel


class Config(BaseIDModel, ConfigBase, table=True): ...
