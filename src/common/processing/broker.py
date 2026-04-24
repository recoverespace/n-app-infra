import logging
from faststream.redis import RedisBroker
from common.settings import settings

broker = RedisBroker(
    str(settings.REDIS_DSN), log_level=logging.DEBUG
)


async def get_broker():
    await broker.start()
    return broker
