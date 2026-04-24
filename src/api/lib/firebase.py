import asyncio
from dataclasses import dataclass
from functools import partial

from api.settings import settings
from api.utils import generate_username
from fastapi import HTTPException, status
from firebase_admin import auth
from sqlmodel import col, and_
from common.otel import get_logger
from data.domain.users.models import User
from data.domain.users.crud import user_crud
from data.domain.tenants.crud import tenant_crud
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)


@dataclass
class FirebaseUser:
    external_id: str
    first_name: str | None
    last_name: str | None
    avatar_url: str | None
    display_name: str | None
    email: str | None


def _extract_name(name: str) -> tuple[str | None, str | None]:
    if name:
        names = str(name).strip().split(maxsplit=1)
        first_name = names[0] if names else None
        last_name = names[1] if len(names) > 1 else None
        return first_name, last_name
    return None, None


async def firebase_verify(token: str) -> FirebaseUser | None:
    try:
        loop = asyncio.get_event_loop()
        decoded_token = await loop.run_in_executor(None, auth.verify_id_token, token)
    except Exception:
        return None

    first_name, last_name = _extract_name(decoded_token.get("name"))
    return FirebaseUser(
        external_id=decoded_token["uid"],
        first_name=first_name,
        last_name=last_name,
        avatar_url=decoded_token.get("picture"),
        display_name=decoded_token.get("name"),
        email=decoded_token.get("email"),
    )


async def check_firebase_user(email: str) -> str | None:
    try:
        loop = asyncio.get_event_loop()
        user = await loop.run_in_executor(
            None,
            partial(auth.get_user_by_email, email=email),
        )
        return user.uid
    except Exception as exc:
        logger.warning(f"Check user={email}. reason={str(exc)}")
    return False


async def create_firebase_user(uid: str, display_name: str, email: str, password: str) -> bool:
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(auth.create_user, uid=uid, display_name=display_name, email=email, email_verified=True),
        )
        logger.info(f"Created user={email}")
        return True
    except Exception as exc:
        logger.warning("Create user={}. reason={}", email, repr(exc))
    return False


async def firebase_delete_user(user_id: str):
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, auth.delete_user, user_id)
    except Exception as exc:
        logger.warning("Can delete user={}. reason={}", user_id, repr(exc))


def get_firebase_name(token):  # pragma: no cover
    name = token.get("name")
    if name:
        name = str(name).strip().split(maxsplit=1)
        first_name = name[0] if name else None
        last_name = name[1] if len(name) > 1 else None
        return first_name, last_name
    return None, None


async def get_firebase_user(token: str, db: AsyncSession) -> User:
    _user = await firebase_verify(token)
    if not _user:
        logger.warning(f"Can not verify id token={token}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Can not verify token")

    tenant_id = 0
    if settings.TENANT_REQUIRED:
        if not _user.email:
            logger.warning("Firebase user has no email")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email is required")
        domain = _user.email.split("@")[-1]
        tenant = await tenant_crud.get_by_domain(domain, db=db)
        if not tenant:
            logger.warning(f"Tenant for domain={domain} not found")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid tenant")
        tenant_id = tenant.id

    display_name = _user.display_name or generate_username()
    user = await user_crud.get_or_create(
        and_(
            col(User.uid) == _user.external_id, col(User.is_active).is_(True), col(User.is_deleted).is_(False)
        ),
        User(
            uid=_user.external_id,
            is_active=True,
            first_name=_user.first_name,
            last_name=_user.last_name,
            avatar_url=_user.avatar_url,
            email=_user.email,
            display_name=display_name,
            tenant_id=tenant_id,
        ),
        db=db,
    )
    return user
