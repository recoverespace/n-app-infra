from data.domain.users.schemas import (
    UserCreate,
    UserUpdate,
    UserRefreshTokenCreate,
    UserRefreshTokenUpdate,
)
from data.domain.users.models import User, UserRefreshToken

from data.lib.crud import CRUDBase


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]): ...


user_crud = CRUDUser(User)


class CRUDUserRefreshToken(CRUDBase[UserRefreshToken, UserRefreshTokenCreate, UserRefreshTokenUpdate]): ...


user_refresh_token_crud = CRUDUserRefreshToken(UserRefreshToken)
