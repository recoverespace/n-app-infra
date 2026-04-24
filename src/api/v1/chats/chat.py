from fastapi import APIRouter, status
from fastapi_pagination import Page
from api.lib.deps import UserIDDep
from api.settings import settings
from api.v1.chats.schemas import CentrifugeInfoModel
from data.domain.chats.crud import chat_crud
from data.domain.chats.models import Chat
from data.domain.chats.schemas import ChatCreate, ChatRead
from sqlmodel import and_, col
from api.lib.deps import DBDep
from data.domain.intents.state import ChatState

router = APIRouter()


@router.get("/")
async def get_chats(user_id=UserIDDep, db=DBDep) -> Page[Chat]:
    return await chat_crud.get_multi_paginated_ordered(
        condition=Chat.user_id == user_id,
        order_by=[col(Chat.created_at).desc()],
        db=db,
    )


@router.post("/")
async def create_chat(data: ChatCreate, user_id=UserIDDep, db=DBDep) -> ChatRead:
    data.user_id = user_id
    data.state = ChatState.default(user_id=user_id)
    chat = await chat_crud.create(data, db=db)
    return ChatRead.model_validate(chat)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: int, user_id=UserIDDep, db=DBDep):
    await chat_crud.remove(and_(chat_crud.model.user_id == user_id, chat_crud.model.id == chat_id), db=db)


@router.get("/centrifuge-info")
async def get_centrifuge_info(user_id=UserIDDep) -> CentrifugeInfoModel:
    return CentrifugeInfoModel(
        connection_url=f"{settings.CENTRIFUGE_WS_SCHEMA}://{settings.CENTRIFUGE_HOST}/connection/websocket",
        channel_name=settings.CENTRIFUGE_CHAT_NAMESPACE_TEMPLATE.format(user_id),
    )
