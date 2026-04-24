# from httpx import AsyncClient
# from sqlmodel.ext.asyncio.session import AsyncSession

# from data.domain.devices.models import Device
# from data.domain.devices.crud import device_crud
# from api.tests.fake.device import device_factory
# from api.tests.urls import DEVICE_INIT, DEVICE_MY, DEVICE_REFRESH_TOKEN
# from api.tests.utils import get_token_headers, init_device


# async def test_init_new_device(client: AsyncClient) -> None:
#     device_data = device_factory(id=None)
#     response = await client.post(DEVICE_INIT, json=device_data)
#     response_data = response.json()
#     assert response.status_code == 200
#     assert response_data["device_id"]
#     created_device_id = response_data["device_id"]
#     token_headers = get_token_headers(response_data)
#     assert token_headers
#     response = await client.get(DEVICE_MY, headers=token_headers)
#     response_data = response.json()
#     assert response_data["id"] == created_device_id


# async def test_update_device(client: AsyncClient, session: AsyncSession):
#     _device = await init_device(client)
#     updated_device = device_factory(id=_device.id)
#     response = await client.post(DEVICE_INIT, json=updated_device)
#     response_data = response.json()
#     assert response.status_code == 200
#     assert response_data["device_id"] == _device.id

#     new_device = await device_crud.get(Device.id == _device.id, session=session)
#     assert new_device.idfa == updated_device["idfa"]

#     # device_change = await device_changes_crud.get(DeviceChanges.device_id == _device.id, session=session)
#     # assert device_change.idfa == _device.device_data["idfa"]


# async def test_device_token_required(client: AsyncClient):
#     response = await client.get(DEVICE_MY)
#     response_data = response.json()
#     assert response.status_code == 403
#     assert response_data["detail"] == "Not authenticated"


# async def test_device_refresh_token(client: AsyncClient):
#     new_device = await init_device(client)
#     test_response = await client.get(DEVICE_MY, headers=new_device.token_headers)
#     assert test_response.status_code == 200

#     refresh_response = await client.post(
#         DEVICE_REFRESH_TOKEN, json={"refresh_token": new_device.refresh_token}
#     )
#     refresh_json = refresh_response.json()
#     assert refresh_response.status_code == 200
#     new_token_headers = get_token_headers(refresh_json)
#     assert new_device.refresh_token != refresh_json["refresh_token"]
#     test_response = await client.get(DEVICE_MY, headers=new_token_headers)
#     assert test_response.status_code == 200
