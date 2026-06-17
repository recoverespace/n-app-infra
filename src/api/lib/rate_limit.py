from __future__ import annotations

from redis.asyncio import Redis


class RateLimitExceeded(Exception):
    pass


_INCR_EXPIRE_LUA = """
local key = KEYS[1]
local ttl = tonumber(ARGV[1])
local current = redis.call('INCR', key)
if current == 1 then
  redis.call('EXPIRE', key, ttl)
end
return current
"""


async def enforce_rate_limit(*, redis: Redis, key: str, limit: int, window_seconds: int) -> int:
    """Increment a counter in Redis with TTL and raise if limit exceeded.

    Returns the new counter value.
    """
    if limit <= 0:
        return 0

    current = int(await redis.eval(_INCR_EXPIRE_LUA, 1, key, window_seconds))
    if current > limit:
        raise RateLimitExceeded()
    return current

