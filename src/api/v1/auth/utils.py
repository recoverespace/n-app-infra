from datetime import UTC, datetime, timedelta
from fastapi import HTTPException, status
from sqlmodel import and_, col
from api.lib.jwt import generate_tokens
from api.v1.auth.schemas import TokenModel
from data.domain.users.models import User, UserRefreshToken
from data.domain.users.crud import user_refresh_token_crud

from sqlmodel.ext.asyncio.session import AsyncSession
from api.settings import settings
from data.domain.users.schemas.usertokens import UserRefreshTokenCreate
from common.otel import get_logger

logger = get_logger(__name__)


async def create_tokens(
    user: User,
    db: AsyncSession,
    expire=True,
    disable_refresh: bool = False,
) -> TokenModel:
    assert user.id is not None
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden access for deactivated user"
        )
    pairs = generate_tokens(
        key=settings.SECRET_KEY,
        sub=str(user.id),
        iss=settings.PROJECT,
        tenant_id=user.tenant_id or 0,
        access_token_ttl=settings.ACCESS_TOKEN_EXPIRE_SECONDS if expire else None,
        refresh_token_ttl=settings.REFRESH_TOKEN_EXPIRE_SECONDS if (expire and not disable_refresh) else None,
        uid=user.id,
    )
    logger.info(f"Generated tokens for user {user.id}: {pairs}")
    if pairs.refresh_token:
        await user_refresh_token_crud.create(
            obj_in=UserRefreshTokenCreate(
                user_id=user.id,
                token=pairs.refresh_token,
                expire_at=datetime.fromtimestamp(pairs.refresh_token_expire_at),
            ),
            db=db,
        )
    access_token_sec = settings.ACCESS_TOKEN_EXPIRE_SECONDS if expire else 999999999
    refresh_token_sec = settings.REFRESH_TOKEN_EXPIRE_SECONDS
    return TokenModel(
        access_token=pairs.access_token,
        refresh_token=pairs.refresh_token if not disable_refresh else None,
        access_token_expires_in=access_token_sec,
        refresh_token_expires_in=refresh_token_sec,
        access_token_expires_at=datetime.now(UTC) + timedelta(seconds=access_token_sec),
        refresh_token_expires_at=datetime.now(UTC) + timedelta(seconds=refresh_token_sec),
    )


async def refresh_tokens(refresh_token: str, db: AsyncSession):
    user_refresh_token = await user_refresh_token_crud.get(
        and_(col(UserRefreshToken.token) == refresh_token, col(UserRefreshToken.expire_at) >= datetime.now()),
        db=db,
    )
    if not user_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    await user_refresh_token_crud.remove(col(UserRefreshToken.id) == user_refresh_token.id, db=db)
    return await create_tokens(user_refresh_token.user, db=db)
