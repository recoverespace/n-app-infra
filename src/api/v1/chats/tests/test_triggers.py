from httpx import AsyncClient

from api.lib.tests.urls import CHATS
from api.lib.tests.utils import init_chat
from api.dialog_processors import process_dialog_message

from api.dialogs import GREETING_TEXT, GREETING_TEST_TEXT, CANCEL_TEXT, CANCEL_SUGGESTION_TEXT


async def mock_dialog_trigger(data):
    await process_dialog_message(data)


async def test_trigger_greeting(client: AsyncClient, mocker):
    mocker.patch("api.v1.chats.messages.dialog_trigger", mock_dialog_trigger)

    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.put(messages_url, params={"kind": "greetings"}, headers=chat.user.token_headers)
    assert response.status_code == 204

    response = await client.get(messages_url, headers=chat.user.token_headers)
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3
    assert response.json()["items"][2]["text"] == GREETING_TEXT.strip()
    assert response.json()["items"][0]["text"] == GREETING_TEST_TEXT.strip()
    assert response.json()["items"][0]["suggestions"] is not None\
    
    print(response.json()["items"][0]["suggestions"])
    assert len(response.json()["items"][0]["suggestions"]["values"]) > 0


async def test_trigger_test_cancel(client: AsyncClient, mocker):
    mocker.patch("api.v1.chats.messages.dialog_trigger", mock_dialog_trigger)

    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.put(messages_url, params={"kind": "cancel_test"}, headers=chat.user.token_headers)
    assert response.status_code == 204

    response = await client.get(messages_url, headers=chat.user.token_headers)
    print(response.json())
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["items"][1]["text"] == CANCEL_TEXT.strip()
    assert response.json()["items"][0]["text"] == CANCEL_SUGGESTION_TEXT.strip()

async def test_trigger_test_start(client: AsyncClient, mocker):
    mocker.patch("api.v1.chats.messages.dialog_trigger", mock_dialog_trigger)

    chat = await init_chat(client)
    messages_url = f"{CHATS}{chat.id}/messages/"
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    response = await client.put(messages_url, params={"kind": "test_end", "value": "10"}, headers=chat.user.token_headers)
    assert response.status_code == 204

    response = await client.get(messages_url, headers=chat.user.token_headers)
    print(response.json())
    assert response.status_code == 200
    assert len(response.json()["items"]) == 2
    assert response.json()["items"][1]["text"] == CANCEL_TEXT.strip()
    assert response.json()["items"][0]["text"] == CANCEL_SUGGESTION_TEXT.strip()
