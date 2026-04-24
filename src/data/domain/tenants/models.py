from data.domain.tenants.schemas import TenantBase
from data.lib.model import BaseIDModel


class Tenant(BaseIDModel, TenantBase, table=True): ...
