import uuid

from fastapi import APIRouter, Body
from sqlmodel import col

from api.settings import settings
from api.lib.centrifuge import generate_centrifugal_token
from api.lib.deps import DBDep, UserIDDep
from api.lib.firebase import get_firebase_user
from api.v1.auth.schemas import (
    CentrifugalRefreshTokenResponseModel,
    FirebaseTokenModel,
    RefreshAccessTokenRequestModel,
    TokenModel,
)
from api.v1.auth.utils import create_tokens, refresh_tokens
from api.utils import generate_username
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from data.domain.tenants.crud import tenant_crud
from data.domain.tenants.models import Tenant


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/anonymous")
async def anonymous_login(user_id: str | None = Body(None, embed=True), db=DBDep) -> TokenModel:
    if settings.ANONYMOUS_ACCESS_ENABLED is False:
        raise PermissionError("Access is disabled.")
    uid = user_id or str(uuid.uuid4())
    user: User = await user_crud.get_or_create(
        col(User.uid) == uid, User(uid=uid, is_active=True, display_name=generate_username()), db=db
    )
    return await create_tokens(user, db)


@router.post("/domain-check")
async def domain_check(email: str = Body(..., embed=True), db=DBDep) -> dict:
    domain = email.split("@")[-1]
    tenant = await tenant_crud.get_by_domain(domain, db=db)
    return {"exists": tenant is not None, "name": tenant.name if tenant else None}


@router.post("/login")
async def firebase_login(data: FirebaseTokenModel, db=DBDep) -> TokenModel:
    user = await get_firebase_user(data.token, db=db)
    return await create_tokens(user, db)


@router.post("/token/refresh")
async def refresh_access_token(data: RefreshAccessTokenRequestModel, db=DBDep) -> TokenModel:
    return await refresh_tokens(refresh_token=data.refresh_token, db=db)


@router.post("/centrifuge/refresh/")
async def refresh_token(user_id=UserIDDep, db=DBDep) -> CentrifugalRefreshTokenResponseModel:
    return generate_centrifugal_token(user=str(user_id))

@router.get("/email-link-login")
async def email_link_login():
    return {"status": "ok", "message": "Link received. Please open the app."}
