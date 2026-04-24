from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import SQLModel, Field, Column, Text


class TenantBase(SQLModel):
    title: str = Field(sa_column=Column("Tenant", Text, nullable=False, unique=True))
    enabled: bool = Field(default=True, nullable=False)
    domains: list[str] = Field(default=[], sa_column=Column(ARRAY(Text), nullable=False))


class TenantUpdate(TenantBase): ...


class TenantCreate(TenantBase): ...


class TenantRead(TenantBase):
    id: int
