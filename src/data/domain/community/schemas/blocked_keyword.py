from sqlmodel import SQLModel, Field


class BlockedKeywordBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    keyword: str = Field(max_length=200, description="Keyword to block", index=True)
    active: bool = Field(default=True, description="Whether keyword filtering is active")


class BlockedKeywordCreate(BlockedKeywordBase):
    pass


class BlockedKeywordUpdate(SQLModel):
    keyword: str | None = None
    active: bool | None = None
