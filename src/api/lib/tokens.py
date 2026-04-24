from datetime import timedelta
from enum import Enum
from redis.asyncio import Redis

from data.domain.users import User


class TokenType(str, Enum):
    ACCESS = "access_token"
    REFRESH = "refresh_token"


async def add_token_to_redis(
    redis_client: Redis,
    user: User,
    token: str,
    token_type: TokenType,
    expire_time: int = 3600,
):
    assert user.id is not None
    token_key = f"user:{user.id}:{token_type}"
    valid_tokens = await get_valid_tokens(redis_client, user.id, token_type)
    await redis_client.sadd(token_key, token)  # type: ignore
    if not valid_tokens:
        await redis_client.expire(token_key, timedelta(minutes=expire_time))


async def get_valid_tokens(redis_client: Redis, user_id: int, token_type: TokenType):
    token_key = f"user:{user_id}:{token_type}"
    valid_tokens = await redis_client.smembers(token_key)  # type: ignore
    return valid_tokens


async def delete_tokens(redis_client: Redis, user: User, token_type: TokenType):
    token_key = f"user:{user.id}:{token_type}"
    valid_tokens = await redis_client.smembers(token_key)  # type: ignore
    if valid_tokens is not None:
        await redis_client.delete(token_key)
