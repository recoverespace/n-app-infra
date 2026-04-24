import logging
from faststream.redis import RedisBroker
from api.settings import settings

broker = RedisBroker(
    str(settings.REDIS_DSN), log_level=logging.DEBUG
)
