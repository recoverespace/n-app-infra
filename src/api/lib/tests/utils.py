import random
import string
from datetime import datetime, timedelta
from dataclasses import dataclass

from api.lib.tests.fake.device import device_factory
from api.lib.tests.fake.types import fake_uuid
from api.lib.tests.urls import AUTH_ANONYMOUS, CHATS, DEVICE_INIT, USERS_ME, USERS_ME_FACTS
from data.domain.tenants.crud import tenant_crud
from data.domain.tenants.schemas import TenantCreate


def random_lower_string() -> str:
    return "".join(random.choices(string.ascii_lowercase, k=32))


def get_token_headers(response: dict[str, str]) -> dict[str, str]:
    a_token = response.get("access_token")
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers


@dataclass
class NewDevice:
    id: str
    device_data: dict[str, str]
    token_headers: dict[str, str]
    refresh_token: str

@dataclass
class NewTenant:
    id: str
    title: str
    domains: list[str]



@dataclass
class NewUser:
    id: str
    user_data: dict[str, str]
    token_headers: dict[str, str]
    refresh_token: str


@dataclass
class NewChat:
    id: str
    name: str
    user: NewUser


async def init_device(client) -> NewDevice:
    device_data = device_factory(id=None)
    response = await client.post(DEVICE_INIT, json=device_data)
    response_data = response.json()
    return NewDevice(
        id=response_data["device_id"],
        device_data=device_data,
        token_headers=get_token_headers(response_data),
        refresh_token=response_data["refresh_token"],
    )

async def init_user(c) -> NewUser:
    user_data = {"external_id": fake_uuid()}
    response = await c.post(AUTH_ANONYMOUS, json=user_data)
    response_data = response.json()
    user_headers = get_token_headers(response_data)
    user = await c.get(USERS_ME, headers=user_headers)
    return NewUser(
        id=user.json()["id"],
        user_data=user_data,
        token_headers=user_headers,
        refresh_token=response_data["refresh_token"],
    )


async def init_chat(client) -> NewChat:
    user = await init_user(client)
    chat_name = fake_uuid()
    response = await client.post(CHATS, json={"name": chat_name}, headers=user.token_headers)
    response_data = response.json()
    return NewChat(id=response_data["id"], name=chat_name, user=user)


async def add_message(client, chat: NewChat, text: str, created_at: datetime | None = None) -> dict:
    messages_url = f"{CHATS}{chat.id}/messages/"
    message = {"uid": fake_uuid(), "text": text, "attachments": [], "created_at": created_at.isoformat() if created_at else datetime.now().isoformat()}
    response = await client.post(messages_url, json=message, headers=chat.user.token_headers)
    assert response.status_code == 202, response.text
    return response.json()


async def add_fact(
    client,
    user: NewUser,
    kind: str,
    label: str,
    value: str,
    extra: dict[str, str] | None = None,
    age_days: int = 0,
    created_at: datetime | None = None
) -> dict:
    created_at = created_at or (datetime.now() - timedelta(days=age_days) if age_days > 0 else datetime.now())
    response = await client.post(
        USERS_ME_FACTS,
        json={
            "kind": kind,
            "label": label,
            "value": value,
            "extra": extra or {},
            "created_at": created_at.isoformat(),
        },
        headers=user.token_headers,
    )
    assert response.status_code == 201, response.text


async def init_tenant(db, title: str, domains: list[str], enabled: bool = True) -> NewTenant:
    """Create a tenant directly using tenant_crud for testing."""
    tenant_data = TenantCreate(title=title, domains=domains, enabled=enabled)
    tenant = await tenant_crud.create(obj_in=tenant_data, db=db)
    return NewTenant(id=tenant.id, title=tenant.title, domains=tenant.domains)
