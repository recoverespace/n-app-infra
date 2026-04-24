import pytest
from httpx import AsyncClient

from api.lib.tests.fake.types import fake_uuid
from api.lib.tests.fake.user import firebase_user_factory
from api.lib.tests.urls import (
    AUTH_FIREBASE,
    USERS_ME,
    USERS_ME_SETTINGS,
)
from api.lib.tests.utils import get_token_headers, init_user


async def test_update_user(client: AsyncClient):
    user = await init_user(client)
    response = await client.patch(USERS_ME, json={"display_name": "Maria"}, headers=user.token_headers)
    assert response.status_code == 204, response.text
    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Maria"
    assert response.json()["created_at"] != ""
    response = await client.patch(USERS_ME, json={"first_name": "Maria"}, headers=user.token_headers)
    assert response.status_code == 204, response.text
    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200, response.text
    assert response.json()["display_name"] == "Maria"


async def test_update_settings_user(client: AsyncClient):
    user = await init_user(client)
    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["settings"]["is_onboarding_finished"] is False

    response = await client.patch(
        USERS_ME_SETTINGS, json={"is_onboarding_finished": True}, headers=user.token_headers
    )
    assert response.status_code == 204

    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["settings"]["is_onboarding_finished"] is True


async def test_update_user_source(client: AsyncClient):
    user = await init_user(client)
    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["settings"]["user_source"] is None

    response = await client.patch(
        USERS_ME_SETTINGS, json={"user_source": "test"}, headers=user.token_headers
    )
    assert response.status_code == 204

    response = await client.get(USERS_ME, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["settings"]["user_source"] == "test"


# async def test_get_device_settings(client: AsyncClient):
#     user = await init_user(client)
#     response = await client.get(USERS_DEVICE_SETTINGS, headers=user.token_headers)
#     assert response.status_code == 200
#     assert response.json()["notification_enabled"] is False


# async def test_update_device_settings(client: AsyncClient):
#     user = await init_user(client)
#     response = await client.post(
#         USERS_DEVICE_SETTINGS,
#         json={
#             "notification_enabled": True,
#             "notification_platform": "ios",
#             "notification_token": fake_uuid(),
#         },
#         headers=user.token_headers,
#     )
#     assert response.status_code == 201
#     response = await client.get(USERS_DEVICE_SETTINGS, headers=user.token_headers)
#     assert response.status_code == 200
#     assert response.json()["notification_enabled"] is True

async def test_users_delete_me(client: AsyncClient, mocker) -> None:
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

    mocker.patch("api.lib.firebase.firebase_delete_user", return_value=None)
    response = await client.delete(USERS_ME, headers=user_token)
    assert response.status_code == 204, response.text

    test_response = await client.get(USERS_ME, headers=user_token)
    assert test_response.status_code == 404
