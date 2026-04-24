from data.lib.model import BaseIDModel
from data.domain.intents.schemas import TemplateOverrideBase

class TemplateOverride(BaseIDModel, TemplateOverrideBase, table=True):
    ...
