import html
import uuid

from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse
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

@router.get("/email-link-login", response_class=HTMLResponse)
async def email_link_login(request: Request) -> HTMLResponse:
    """Universal-link fallback page for Firebase email magic links.

    The endpoint is the `continueUrl` configured for `sendSignInLinkToEmail`.
    If iOS Universal Links / Android App Links work, the app is opened
    directly by the OS and this handler is never hit. When the user lands
    in a browser instead, we render a page with a single "Open in app"
    button. Important: do NOT auto-redirect (meta refresh / JS replace) to
    the same URL — Universal Links fire only on a user-initiated tap, so
    auto-redirect creates an infinite loop in Safari. The button below is
    a real <a href> link, so tapping it triggers Universal Link handling.
    """

    base = settings.EXTERNAL_URL.rstrip("/")
    query = f"?{request.url.query}" if request.url.query else ""
    app_url = f"{base}{request.url.path}{query}"
    href_url = html.escape(app_url, quote=True)

    # Custom-scheme fallback for users whose browser does not honour the
    # Universal Link (e.g. Mail / Gmail in-app browser on iOS, or older
    # Android). Tapping this opens the app directly via the `recovered://`
    # scheme. Query is preserved verbatim from the request.
    scheme_url = f"recovered://email-link-login{query}"
    scheme_href = html.escape(scheme_url, quote=True)

    body = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Open in app</title>
    <style>
      body {{
        margin: 0;
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto,
          Helvetica, Arial, sans-serif;
        background: #f3eee7;
        color: #2b2b2b;
      }}
      .card {{
        max-width: 360px;
        margin: 24px;
        padding: 24px;
        text-align: center;
      }}
      h1 {{ font-size: 20px; margin: 0 0 12px; }}
      p {{ margin: 0 0 24px; font-size: 15px; line-height: 1.4; opacity: 0.8; }}
      .button {{
        display: inline-block;
        padding: 12px 24px;
        background: #2b2b2b;
        color: #ffffff;
        text-decoration: none;
        border-radius: 999px;
        font-weight: 600;
        margin-bottom: 12px;
      }}
      .button-secondary {{
        background: transparent;
        color: #2b2b2b;
        border: 1px solid #2b2b2b;
        margin-bottom: 0;
      }}
    </style>
  </head>
  <body>
    <main class=\"card\">
      <h1>Almost there</h1>
      <p>Tap the button below to finish signing in inside the app.</p>
      <a class=\"button\" href=\"{href_url}\">Open in app</a>
      <a class=\"button button-secondary\" href=\"{scheme_href}\">Open the app another way</a>
    </main>
  </body>
</html>
"""
    return HTMLResponse(content=body)
