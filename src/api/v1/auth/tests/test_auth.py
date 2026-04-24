from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.lib.tests.fake.types import fake_uuid
from api.lib.tests.fake.user import firebase_user_factory
from api.lib.tests.urls import (
    AUTH_ANONYMOUS,
    AUTH_CENTRIFUGE_REFRESH_TOKEN,
    AUTH_FIREBASE,
    AUTH_REFRESH_TOKEN,
    USERS_ME,
)
from api.lib.tests.utils import get_token_headers, init_user, init_tenant


async def test_auth_anonymous(client: AsyncClient) -> None:
    response = await client.post(AUTH_ANONYMOUS, json={"external_id": fake_uuid()})
    response_data = response.json()
    assert response.status_code == 200
    assert response_data["access_token"]


async def test_auth_refresh_token(client: AsyncClient) -> None:
    new_user = await init_user(client)
    test_response = await client.get(USERS_ME, headers=new_user.token_headers)
    assert test_response.status_code == 200

    refresh_response = await client.post(AUTH_REFRESH_TOKEN, json={"refresh_token": new_user.refresh_token})
    refresh_json = refresh_response.json()
    assert refresh_response.status_code == 200
    new_token_headers = get_token_headers(refresh_json)
    assert new_user.refresh_token != refresh_json["refresh_token"]
    test_response = await client.get(USERS_ME, headers=new_token_headers)
    assert test_response.status_code == 200


async def test_auth_firebase_invalid_token(client: AsyncClient, mocker) -> None:
    mocker.patch("api.lib.firebase.firebase_verify", return_value=None)
    response = await client.post(AUTH_FIREBASE, json={"token": fake_uuid()})
    response_data = response.json()
    assert response.status_code == 401
    assert response_data["detail"] == "Can not verify token"


async def test_auth_firebase(client: AsyncClient, mocker) -> None:
    from api.lib.firebase import FirebaseUser

    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(**firebase_user_factory())
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)
    response = await client.post(
        AUTH_FIREBASE,
        json={"token": firebase_token},
    )
    response_data = response.json()
    assert response.status_code == 200
    assert response_data["access_token"]
    user_token = get_token_headers(response_data)

    response = await client.get(USERS_ME, headers=user_token)
    response_data = response.json()
    assert response.status_code == 200
    assert response_data["id"]
    assert response_data["uid"] == firebase_user.external_id


async def test_centrifuge_refresh_token(client: AsyncClient):
    user = await init_user(client)
    test_response = await client.get(USERS_ME, headers=user.token_headers)
    token_response = await client.post(AUTH_CENTRIFUGE_REFRESH_TOKEN, headers=user.token_headers)
    assert token_response.status_code == 200
    assert str(token_response.json()["id"]) == str(test_response.json()["id"])
    assert token_response.json()["token"]


async def test_centrifuge_refresh_token_without_user(client: AsyncClient):
    token_response = await client.post(AUTH_CENTRIFUGE_REFRESH_TOKEN)
    assert token_response.status_code == 403


# Tenant Integration Tests


async def test_firebase_login_with_valid_tenant(
    client: AsyncClient, session: AsyncSession, mocker
) -> None:
    """Test Firebase login with valid tenant domain when TENANT_REQUIRED=True."""
    from api.lib.firebase import FirebaseUser

    # Create tenant
    tenant = await init_tenant(session, "Test Company", ["testcompany.com"])

    # Mock settings to require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", True)

    # Create Firebase user with email from tenant domain
    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(
        **firebase_user_factory(email="user@testcompany.com")
    )
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    # Login should succeed
    response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["access_token"]

    # Verify user was created with correct tenant_id
    user_headers = get_token_headers(response_data)
    user_response = await client.get(USERS_ME, headers=user_headers)
    assert user_response.status_code == 200
    user_data = user_response.json()
    assert user_data["tenant_id"] == tenant.id


async def test_firebase_login_with_invalid_tenant_fails(
    client: AsyncClient, session: AsyncSession, mocker
) -> None:
    """Test Firebase login fails with invalid tenant domain when TENANT_REQUIRED=True."""
    from api.lib.firebase import FirebaseUser

    # Create a tenant but use different domain
    await init_tenant(session, "Test Company", ["testcompany.com"])

    # Mock settings to require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", True)

    # Create Firebase user with email from non-existent tenant domain
    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(
        **firebase_user_factory(email="user@otherdomain.com")
    )
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    # Login should fail
    response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert response.status_code == 401, response.text
    response_data = response.json()
    assert response_data["detail"] == "Invalid tenant"


async def test_firebase_login_tenant_not_required(
    client: AsyncClient, session: AsyncSession, mocker
) -> None:
    """Test Firebase login succeeds without tenant when TENANT_REQUIRED=False."""
    from api.lib.firebase import FirebaseUser

    # Mock settings to NOT require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", False)

    # Create Firebase user with any email
    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(
        **firebase_user_factory(email="user@anydomain.com")
    )
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    # Login should succeed even without tenant
    response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert response.status_code == 200, response.text
    response_data = response.json()
    assert response_data["access_token"]

    # Verify user was created with tenant_id=0 (default)
    user_headers = get_token_headers(response_data)
    user_response = await client.get(USERS_ME, headers=user_headers)
    assert user_response.status_code == 200
    user_data = user_response.json()
    assert user_data["tenant_id"] == 0


async def test_firebase_login_no_email_tenant_required(
    client: AsyncClient, mocker
) -> None:
    """Test Firebase login fails when tenant required but user has no email."""
    from api.lib.firebase import FirebaseUser

    # Mock settings to require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", True)

    # Create Firebase user without email
    firebase_token = fake_uuid()
    firebase_user_data = firebase_user_factory()
    firebase_user_data["email"] = None  # No email
    firebase_user = FirebaseUser(**firebase_user_data)
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    # Login should fail
    response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert response.status_code == 401, response.text
    response_data = response.json()
    assert response_data["detail"] == "Email is required"


async def test_token_includes_tenant_id(
    client: AsyncClient, session: AsyncSession, mocker
) -> None:
    """Test that JWT token includes tenant_id in payload."""
    from api.lib.firebase import FirebaseUser
    import jwt
    from api.settings import settings

    # Create tenant
    tenant = await init_tenant(session, "Token Test Company", ["tokentest.com"])

    # Mock settings to require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", True)

    # Create Firebase user
    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(
        **firebase_user_factory(email="user@tokentest.com")
    )
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    # Login
    response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert response.status_code == 200
    response_data = response.json()

    # Decode token and verify tenant_id is in payload
    access_token = response_data["access_token"]
    decoded = jwt.decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "tenant_id" in decoded
    assert decoded["tenant_id"] == tenant.id


async def test_token_refresh_preserves_tenant_id(
    client: AsyncClient, session: AsyncSession, mocker
) -> None:
    """Test that token refresh preserves tenant_id."""
    from api.lib.firebase import FirebaseUser
    import jwt
    from api.settings import settings

    # Create tenant
    tenant = await init_tenant(session, "Refresh Test Company", ["refreshtest.com"])

    # Mock settings to require tenant
    mocker.patch("api.lib.firebase.settings.TENANT_REQUIRED", True)

    # Create Firebase user and login
    firebase_token = fake_uuid()
    firebase_user = FirebaseUser(
        **firebase_user_factory(email="user@refreshtest.com")
    )
    mocker.patch("api.lib.firebase.firebase_verify", return_value=firebase_user)

    login_response = await client.post(AUTH_FIREBASE, json={"token": firebase_token})
    assert login_response.status_code == 200
    login_data = login_response.json()

    # Refresh token
    refresh_response = await client.post(
        AUTH_REFRESH_TOKEN, json={"refresh_token": login_data["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()

    # Verify new token still has tenant_id
    new_access_token = refresh_data["access_token"]
    decoded = jwt.decode(new_access_token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "tenant_id" in decoded
    assert decoded["tenant_id"] == tenant.id
