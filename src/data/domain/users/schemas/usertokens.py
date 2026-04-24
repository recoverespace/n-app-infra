from datetime import datetime

from pydantic.json_schema import SkipJsonSchema
from sqlmodel import Field, SQLModel, Column, Integer, ForeignKey


class UserRefreshTokenBase(SQLModel):
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE"))
    )
    token: str
    expire_at: datetime


class UserRefreshTokenCreate(UserRefreshTokenBase):
    user_id: SkipJsonSchema[int] = Field(exclude=True)


class UserRefreshTokenUpdate(UserRefreshTokenBase): ...


class UserRefreshTokenRead(UserRefreshTokenBase):
    id: int
