from datetime import timedelta
import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2AuthorizationCodeBearer
from faststream.redis import RedisBroker
from jwt import PyJWTError
from redis.asyncio import Redis
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import and_, col
from opentelemetry import trace

from api.lib.centrifuge import Centrifuge, centrifuge
from api.lib.jwt import validate_token, JWT_ALGORITHM
from api.settings import settings
from data.domain.users.crud import user_crud as user_crud
from data.domain.users.models import User
from data.domain.chat_messages.models import ChatMessage
from data.domain.chat_messages.crud import chat_message_crud
from data.domain.chats.models import Chat
from data.domain.chats.crud import chat_crud
from data.lib.db import SessionLocal

reusable_oauth2 = OAuth2AuthorizationCodeBearer(
    authorizationUrl="/api/v1/auth",
    tokenUrl="/api/v1/get_token",
    refreshUrl="/api/v1/refresh_token",
)

broker = RedisBroker(str(settings.REDIS_DSN), log_level=logging.DEBUG)


def get_broker() -> RedisBroker:
    return broker


async def get_redis_client() -> Redis:
    redis = await aioredis.from_url(
        str(settings.REDIS_DSN),
        max_connections=10,
        encoding="utf8",
        decode_responses=True,
    )
    return redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:  # type: ignore
        yield session


def get_centrifuge() -> Centrifuge:
    return centrifuge


RedisDep: Redis = Depends(get_redis_client)
DBDep: AsyncSession = Depends(get_db)
BrokerDep: RedisBroker = Depends(get_broker)
CentrifugeDep: Centrifuge = Depends(get_centrifuge)


async def get_current_user_id(
    request: Request,
    auth: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> int:
    try:
        decoded_token = validate_token(
            settings.SECRET_KEY, auth.credentials, JWT_ALGORITHM, leeway=timedelta(days=2)
        )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{str(exc)}: {request.headers} {request.url} {request.method}",
        ) from exc
    else:
        user_id = int(decoded_token["uid"])
        tenant_id = int(decoded_token.get("tenant_id", 0))
        trace.get_current_span().set_attribute("user_id", user_id)
        trace.get_current_span().set_attribute("tenant_id", tenant_id)
        return user_id


UserIDDep = Depends(get_current_user_id)


async def get_current_user(user_id: int = UserIDDep, db: AsyncSession = DBDep):
    user = await user_crud.get(and_(col(User.id) == user_id, col(User.is_deleted) == False), db=db)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


UserDep: User = Depends(get_current_user)


async def get_chat(
    chat_id: int = 0,
    user_id: int = UserIDDep,
    db: AsyncSession = DBDep,
) -> Chat:
    chat = await chat_crud.get(and_(Chat.id == chat_id, Chat.user_id == user_id), db=db)
    if chat is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    trace.get_current_span().set_attribute("chat_id", chat_id)

    return chat


ChatDep: Chat = Depends(get_chat)


async def get_chat_message(
    message_id: int = 0,
    chat: Chat = ChatDep,
    db: AsyncSession = DBDep,
) -> ChatMessage:
    message = await chat_message_crud.get(
        and_(ChatMessage.id == message_id, ChatMessage.chat_id == chat.id), db=db
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    trace.get_current_span().set_attribute("message_id", message_id)
    return message


MessageDep: ChatMessage = Depends(get_chat_message)


async def verify_reporting_api_key(
    request: Request,
    auth: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=True)),
) -> bool:
    if auth.credentials != settings.REPORTING_API_KEY or not settings.REPORTING_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key for reporting endpoint",
        )
    return True


ReportingAPIKeyDep = Depends(verify_reporting_api_key)
