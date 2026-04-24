import random
import string
from collections import namedtuple
from datetime import UTC, datetime, timedelta
import time

import jwt
from sqlmodel import col
from sqlmodel.ext.asyncio.session import AsyncSession
from common.otel import get_logger


logger = get_logger(__name__)

JWT_ALGORITHM = "HS256"

TokenPair = namedtuple(
    "TokenPair", ("access_token", "access_token_expire_at", "refresh_token", "refresh_token_expire_at")
)


def _generate_refresh_token(n=128):
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def generate_tokens(
    key: str,
    sub: str | int,
    iss: str,
    tenant_id: int | None = None,
    access_token_ttl: int | None = None,
    refresh_token_ttl: int | None = None,
    **extra,
) -> TokenPair:
    now = int(time.time())
    if access_token_ttl:
        access_token_expire_at = now + access_token_ttl
        refresh_token = _generate_refresh_token()
        refresh_token_expire_at = now + (refresh_token_ttl or access_token_ttl)
    else:
        access_token_expire_at = None
        refresh_token = None
        refresh_token_expire_at = None

    payload = {
        "sub": sub,
        "iss": iss,
        "tenant_id": tenant_id,
    } | extra
    if access_token_expire_at:
        payload["exp"] = access_token_expire_at
    access_token = jwt.encode(payload=payload, key=key, algorithm=JWT_ALGORITHM)
    logger.info(f"Generated access token {access_token}")
    return TokenPair(access_token, access_token_expire_at, refresh_token, refresh_token_expire_at)


def validate_token(key: str, token: str, algorithm: str = JWT_ALGORITHM, leeway: float | timedelta = 10):
    return jwt.decode(token, key, algorithms=[algorithm], leeway=leeway)


async def remove_expired_tokens(db: AsyncSession):
    from data.domain.users.crud import user_refresh_token_crud
    from data.domain.users.models import UserRefreshToken

    await user_refresh_token_crud.remove(col(UserRefreshToken.expire_at) <= datetime.now(UTC))
