from datetime import datetime, timedelta
from httpx import AsyncClient

from api.lib.tests.urls import (
    USERS_ME_FACTS,
)
from api.lib.tests.utils import get_token_headers, init_user


async def test_add_fact(client: AsyncClient):
    user = await init_user(client)
    created_at = datetime.now() - timedelta(days=2)
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    response = await client.post(
        USERS_ME_FACTS,
        json={"kind": "test", "label": "Test", "value": "1", "created_at": created_at.isoformat()},
        headers=user.token_headers,
    )
    assert response.status_code == 201, response.text
    response = await client.get(
        USERS_ME_FACTS,
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        headers=user.token_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["kind"] == "test"
    assert response.json()["items"][0]["value"] == "1"
    assert response.json()["items"][0]["created_at"] != ""
    assert response.json()["items"][0]["updated_at"] != ""
    fact_id = response.json()["items"][0]["id"]
    response = await client.patch(
        USERS_ME_FACTS + f"{fact_id}", json={"value": "2"}, headers=user.token_headers
    )
    assert response.status_code == 204, response.text
    response = await client.get(
        USERS_ME_FACTS,
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        headers=user.token_headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["items"][0]["kind"] == "test"
    assert response.json()["items"][0]["value"] == "2"

async def test_fact_filters(client: AsyncClient):
    user = await init_user(client)
    created_at = datetime.now() - timedelta(days=2)
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    num_facts = 10
    for i in range(num_facts):
        fact_created_at = created_at + timedelta(hours=i)
        response = await client.post(
            USERS_ME_FACTS,
            json={"kind": "test", "label": "Test", "value": str(i), "created_at": fact_created_at.isoformat()},
            headers=user.token_headers,
        )
        assert response.status_code == 201, response.text

    response = await client.get(
        USERS_ME_FACTS,
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        headers=user.token_headers,
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == num_facts

    response = await client.get(
        USERS_ME_FACTS,
        params={"start_date": start_date.isoformat(), "end_date": end_date.isoformat(), "size": 5},
        headers=user.token_headers,
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 5
    assert response.json()["items"][0]["value"] == str(num_facts -1)


    response = await client.get(
        USERS_ME_FACTS,
        params={"start_date": end_date.isoformat(), "end_date": end_date.isoformat()},
        headers=user.token_headers,
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 0