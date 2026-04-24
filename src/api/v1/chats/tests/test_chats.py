from httpx import AsyncClient

from api.lib.tests.urls import CHATS, CHATS_CENTRIFUGE_INFO
from api.lib.tests.utils import init_user


async def test_get_centrifuge_info(client: AsyncClient) -> None:
    user = await init_user(client)
    response = await client.get(CHATS_CENTRIFUGE_INFO, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["connection_url"] != ""


async def test_create_chat(client: AsyncClient) -> None:
    user = await init_user(client)
    response = await client.post(CHATS, json={"name": "chat"}, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["id"]

    user = await init_user(client)
    response = await client.get(CHATS, params={"page": 1, "size": 100}, headers=user.token_headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 0
    response = await client.post(CHATS, json={"name": "chat"}, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["id"]
    chat_id = response.json()["id"]

    response = await client.get(CHATS, params={"page": 1, "size": 100}, headers=user.token_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["id"] == chat_id


async def test_delete_chat(client: AsyncClient) -> None:
    user = await init_user(client)
    response = await client.post(CHATS, json={"name": "chat"}, headers=user.token_headers)
    assert response.status_code == 200
    assert response.json()["id"]
    chat_id = response.json()["id"]
    response = await client.delete(f"{CHATS}{chat_id}", headers=user.token_headers)
    assert response.status_code == 204
    ...
