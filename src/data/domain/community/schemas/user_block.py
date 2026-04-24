from sqlmodel import SQLModel, Field


class UserBlockBase(SQLModel):
    tenant_id: int = Field(default=0, index=True, description="Tenant ID for multi-tenancy")
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    reason: str = Field(description="Reason for blocking the user")
    moderator_id: int = Field(foreign_key="user.id", index=True, description="Admin/moderator who blocked the user")


class UserBlockCreate(UserBlockBase):
    pass


class UserBlockUpdate(SQLModel):
    reason: str | None = None
