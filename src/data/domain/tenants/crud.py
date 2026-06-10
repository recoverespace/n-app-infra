from sqlalchemy import any_
from sqlmodel import col, select

from data.domain.tenants.models import Tenant
from data.domain.tenants.schemas import TenantCreate, TenantUpdate
from data.lib.crud import CRUDBase


class CRUDTenant(CRUDBase[Tenant, TenantCreate, TenantUpdate]):


    async def get_by_domain(self, domain: str, **kwargs) -> Tenant | None:
        db = kwargs.get("db")
        if db is None:
            raise ValueError("Database session (db) must be provided as a keyword argument.")

        statement = select(Tenant).where(domain == any_(col(Tenant.domains)))
        result = await db.execute(statement)
        return result.scalars().first()



tenant_crud = CRUDTenant(Tenant)
