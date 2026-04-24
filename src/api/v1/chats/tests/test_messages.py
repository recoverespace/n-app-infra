from httpx import AsyncClient

from api.lib.tests.fake.types import fake_uuid
from api.lib.tests.urls import CHATS
from api.lib.tests.utils import init_chat


async def test_send_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    assert response.json()["text"] == text

    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) > 0
    assert response.json()["items"][0]["created_at"] != ""


async def test_update_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    message_id = response.json()["id"]
    new_text = "New text"
    response = await client.patch(
        f"{messages_url}{message_id}", json={"text": new_text}, headers=chat.user.token_headers
    )
    assert response.status_code == 204
    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert len(response.json()["items"]) == 1, response.text
    assert response.json()["items"][0]["text"] == new_text


async def test_delete_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    assert response.json()["text"] == text
    message_id = response.json()["id"]
    response = await client.delete(f"{messages_url}{message_id}", headers=chat.user.token_headers)
    assert response.status_code == 204
    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert len(response.json()["items"]) == 0


async def test_ack_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    assert response.json()["acked_at"] is None
    message_id = response.json()["id"]
    response = await client.post(f"{messages_url}{message_id}/ack", headers=chat.user.token_headers)
    assert response.status_code == 204, response.text
    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert len(response.json()["items"]) >= 0
    assert response.json()["items"][0]["acked_at"] is not None


async def test_trigger_chat_message(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"

    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.put(f"{messages_url}", headers=chat.user.token_headers)
    assert response.status_code == 204


async def test_feedback_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    message_id = response.json()["id"]
    response = await client.post(
        f"{messages_url}{message_id}/feedbacks/",
        json={"text": "text", "options": []},
        headers=chat.user.token_headers,
    )
    assert response.status_code == 201


async def test_reaction_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    message_id = response.json()["id"]
    response = await client.post(
        f"{messages_url}{message_id}/reactions/",
        json={"reaction_type": "like"},
        headers=chat.user.token_headers,
    )
    assert response.status_code == 201

    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert len(response.json()["items"]) >= 0
    assert len(response.json()["items"][0]["reactions"]) == 1
    reaction = response.json()["items"][0]["reactions"][0]
    assert reaction["reaction_type"] == "like"


async def test_delete_reaction_chat_messages(client: AsyncClient, mocker):
    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    text = fake_uuid()
    message = {"uid": fake_uuid(), "text": text, "attachments": []}
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    message_id = response.json()["id"]
    response = await client.post(
        f"{messages_url}{message_id}/reactions/",
        json={"reaction_type": "like"},
        headers=chat.user.token_headers,
    )
    assert response.status_code == 201

    response = await client.get(messages_url, headers=chat.user.token_headers)
    reaction_id = response.json()["items"][0]["reactions"][0]["id"]

    response = await client.delete(
        f"{messages_url}{message_id}/reactions/{reaction_id}", headers=chat.user.token_headers
    )
    assert response.status_code == 204
    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert len(response.json()["items"][0]["reactions"]) == 0
