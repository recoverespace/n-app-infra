import aiohttp
import json
from aiohttp import ClientError
from api.lib.deps import get_redis_client
from api.settings import settings
from common.otel import get_logger
import redis.asyncio as aioredis

logger = get_logger(__name__)

SAFEGUARDING_TOKEN_KEY = "safeguarding_oauth_token"

class SafeguardingError(Exception):
    """Raised when content fails the safety check (flagged)."""
    pass

class SafeguardingServiceError(Exception):
    """Raised when there is a technical issue with the safety service."""
    pass

def is_enabled() -> bool:
    """Check if the safeguarding feature is enabled in settings."""
    return settings.SAFEGUARDING_ENABLED

async def _get_token_from_cache(redis: aioredis.Redis) -> str | None:
    try:
        return await redis.get(SAFEGUARDING_TOKEN_KEY)
    except Exception as e:
        logger.error(f"Error getting Safeguarding token from Redis: {e}")
        return None

async def _cache_token(redis: aioredis.Redis, token: str, expires_in: int) -> None:
    try:
        # Cushion of 300s to ensure token doesn't expire mid-request
        ttl = max(expires_in - 300, 300)
        await redis.setex(SAFEGUARDING_TOKEN_KEY, ttl, token)
    except Exception as e:
        logger.error(f"Error caching Safeguarding token: {e}")

async def _fetch_new_token(redis: aioredis.Redis) -> str | None:
    """Request a new OAuth token from Microsoft Entra."""
    url = f"https://login.microsoftonline.com/{settings.SAFEGUARDING_TENANT_ID}/oauth2/v2.0/token"
    
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.SAFEGUARDING_CLIENT_ID,
        "client_secret": settings.SAFEGUARDING_CLIENT_SECRET,
        "scope": settings.SAFEGUARDING_API_SCOPE,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                if resp.status != 200:
                    err_body = await resp.text()
                    logger.error(f"Safeguarding Auth Failed: {resp.status} - {err_body}")
                    return None
                
                token_data = await resp.json()
                token = token_data.get("access_token")
                expires = token_data.get("expires_in", 3600)
                
                if token:
                    await _cache_token(redis, token, expires)
                    return token
    except Exception as e:
        logger.error(f"Unexpected error fetching safeguarding token: {e}")
    return None

async def get_token(redis: aioredis.Redis) -> str | None:
    token = await _get_token_from_cache(redis)
    if token:
        return token
    return await _fetch_new_token(redis)

async def check_text_safe(text: str) -> None:
    """
    Analyzes text for safety.
    Raises SafeguardingError if content is flagged.
    Raises SafeguardingServiceError for technical failures.
    """
    if not is_enabled() or not text or not text.strip():
        return

    redis = await get_redis_client()
    try:
        token = await get_token(redis)
        
        # Prepare Azure Gateway request
        url = f"{settings.SAFEGUARDING_BASE_URL.rstrip('/')}/other/tools/azure-content-safety"
        headers = {
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": settings.SAFEGUARDING_SUBSCRIPTION_KEY
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = {
            "text": text,
            "threshold": settings.SAFEGUARDING_THRESHOLD
        }

        async with aiohttp.ClientSession() as session:
            # Set a reasonable timeout (e.g., 5s total)
            timeout = aiohttp.ClientTimeout(total=5)
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as resp:
                
                # Handle expired token (401)
                if resp.status == 401:
                    logger.info("Safeguarding token expired, retrying once...")
                    await redis.delete(SAFEGUARDING_TOKEN_KEY)
                    token = await _fetch_new_token(redis)
                    if token:
                        headers["Authorization"] = f"Bearer {token}"
                        async with session.post(url, json=payload, headers=headers, timeout=timeout) as retry_resp:
                            resp = retry_resp

                if resp.status != 200:
                    err_text = await resp.text()
                    logger.error(f"Safeguarding API error: {resp.status} - {err_text}")
                    raise SafeguardingServiceError("Safety check service is currently unavailable")

                result = await resp.json()
                is_flagged = result.get("data", {}).get("flagged", False)
                
                if is_flagged:
                    max_severity = result.get("data", {}).get("text", {}).get("maxSeverity", "unknown")
                    logger.warning(f"Content blocked by safeguarding. Max Severity: {max_severity}")
                    raise SafeguardingError("Message does not meet safeguarding standards")

    except (ClientError, SafeguardingServiceError) as e:
        logger.error(f"Safeguarding connection/service error: {e}")
        # Defaulting to blocking if the safety check fails technically
        raise SafeguardingServiceError("Service unavailable")
    finally:
        await redis.close()
        