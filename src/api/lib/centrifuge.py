import random
import time

import jwt
from cent import AsyncClient, PublishRequest, PresenceRequest, InfoRequest, InfoResult

from api.settings import settings
from api.v1.auth.schemas import CentrifugalRefreshTokenResponseModel
from common.otel import get_logger

logger = get_logger(__name__)


class Centrifuge:
    chat_namespace_template = settings.CENTRIFUGE_CHAT_NAMESPACE_TEMPLATE

    def __init__(self):
        self._client = None
        self._api_url = f"{settings.CENTRIFUGE_SCHEMA}://{settings.CENTRIFUGE_INTERNAL_HOST}/api"
        self._api_key = settings.CENTRIFUGE_API_KEY

    async def _get_client(self):
        """Get or create the AsyncClient instance"""
        if self._client is None:
            print(self._api_key)
            self._client = AsyncClient(self._api_url, self._api_key)
        return self._client

    async def info(self) -> InfoResult:
        """Ping the Centrifugo server to check connectivity"""
        client = await self._get_client()
        return await client.info(request=InfoRequest(), timeout=1.0)

    async def close(self):
        """Properly close the client"""
        if self._client is not None:
            await self._client.close()  # Check if AsyncClient has a close method
            self._client = None

    async def is_present(self, user_id: str | int) -> bool:
        client = await self._get_client()
        channel = self.chat_namespace_template.format(user_id)
        response = await client.presence(PresenceRequest(channel=channel))
        return len(response.presence) > 0

    async def publish(self, user_id: str | int, data: dict):
        client = await self._get_client()
        channel = self.chat_namespace_template.format(user_id)
        try:
            logger.info(f"Publish message to centrifuge channel={channel} data={data}")
            result = await client.publish(PublishRequest(channel=channel, data=data))
            logger.info(f"Message published to centrifuge channel={channel} result={result}")
        except Exception as exc:
            logger.exception(f"Can not send message to centrifuge exc={exc}")


centrifuge = Centrifuge()


def generate_centrifugal_token(user: str, bias_ttl=0.05) -> CentrifugalRefreshTokenResponseModel:
    secret = settings.CENTRIFUGE_SECRET
    ttl = settings.CENTRIFUGE_TOKEN_TTL
    data = {"sub": user, "channels": [settings.CENTRIFUGE_CHAT_NAMESPACE_TEMPLATE.format(user)]}
    bias = int(ttl * bias_ttl)
    ttl += random.randint(-bias, bias)
    data["exp"] = int(time.time() + ttl)
    logger.info(f"Generate centrifugal token for user={user} ttl={ttl} token={data}")
    token = jwt.encode(data, secret, algorithm="HS256")
    return CentrifugalRefreshTokenResponseModel(id=user, token=token, ttl=ttl)
