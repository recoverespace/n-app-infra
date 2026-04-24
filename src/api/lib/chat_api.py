import aiohttp
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from aiohttp import ClientError, ContentTypeError
from api.lib.deps import get_redis_client
from api.settings import settings
from common.otel import get_logger
import redis.asyncio as aioredis

logger = get_logger(__name__)
CHAT_ENDPOINT = settings.CHAT_URL
OAUTH_REDIS_KEY = "chat_oauth_token"


class ChatServiceError(Exception):
    """Custom exception for chat service errors."""

    pass


@dataclass
class ChatAnswer:
    answer: str
    metadata: dict
    suggestions: list[str] = None


def detect_suggestions(paragraph: str) -> bool:
    return paragraph.startswith("You can respond with:") or paragraph.startswith("•")


def parse_suggestions(suggestion_text: str) -> list[str]:
    suggestions = []
    for line in suggestion_text.split("\n"):
        line = line.strip()
        if line.startswith("•") or line.startswith("-"):
            suggestion = line[1:].strip()
            if suggestion and suggestion != "Type your own answer":
                # Remove any encasing quotes
                suggestion = (
                    suggestion.strip('"').strip("'").strip("“").strip("”").strip("‘").strip("’").strip(".")
                )
                suggestions.append(suggestion)
    return suggestions


def detect_metadata(paragraph: str) -> bool:
    return "```json" in paragraph or paragraph.endswith("```")


def parse_metadata(paragraph: str) -> dict:
    json_start = paragraph.find("```json")
    json_end = paragraph.rfind("```") or len(paragraph)
    try:
        json_text = paragraph[json_start + 7 : json_end].strip()
        return json.loads(json_text)
    except json.JSONDecodeError:
        return {}


def parse_message(message: str) -> ChatAnswer:
    paragraphs = message.split("\n\n")
    answer_finished = False
    first_paragraph = True
    answer = ""
    metadata = {}
    suggestions = []

    for p in paragraphs:
        if not first_paragraph:
            if detect_suggestions(p):
                answer_finished = True
                suggestions = parse_suggestions(p)
                continue

            if detect_metadata(p):
                answer_finished = True
                metadata = parse_metadata(p)
                continue
        first_paragraph = False
        if not answer_finished:
            answer += p.strip() + "\n\n"

    return ChatAnswer(answer.strip(), metadata, suggestions)


def oauth_enabled() -> bool:
    """Check if OAuth is configured."""
    return bool(
        settings.CHAT_OAUTH_CLIENT_ID
        and settings.CHAT_OAUTH_CLIENT_SECRET
        and settings.CHAT_OAUTH_TENANT_ID
        and settings.CHAT_OAUTH_SUBSCRIPTION_KEY
    )


async def get_oauth_token_from_redis(redis: aioredis.Redis) -> str | None:
    """Get cached OAuth token from Redis."""
    if not oauth_enabled():
        return None

    try:
        token = await redis.get(OAUTH_REDIS_KEY)
        return token
    except Exception as e:
        logger.error(f"Error getting OAuth token from Redis: {e}")
        return None


async def cache_oauth_token(redis: aioredis.Redis, token: str, expires_in: int) -> None:
    """Cache OAuth token in Redis with expiration."""
    try:
        # Cache for slightly less time than actual expiration to avoid edge cases
        cache_ttl = max(expires_in - 300, 300)  # Cache for at least 5 minutes
        await redis.setex(OAUTH_REDIS_KEY, cache_ttl, token)
        await redis.close()
    except Exception as e:
        logger.error(f"Error caching OAuth token to Redis: {e}")


async def get_oauth_token(redis: aioredis.Redis) -> str | None:
    """Get OAuth token, either from cache or by requesting a new one."""
    if not oauth_enabled():
        logger.info("OAuth not configured, skipping token retrieval")
        return None

    # Try to get from cache first
    cached_token = await get_oauth_token_from_redis(redis)
    if cached_token:
        logger.info("Using cached OAuth token")
        return cached_token

    # Request new token
    logger.info("Requesting new OAuth token")
    try:
        token_url = f"https://login.microsoftonline.com/{settings.CHAT_OAUTH_TENANT_ID}/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": settings.CHAT_OAUTH_CLIENT_ID,
            "client_secret": settings.CHAT_OAUTH_CLIENT_SECRET,
            "scope": settings.CHAT_OAUTH_SCOPE,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"OAuth token request failed: {response.status} - {error_text}")
                    return None

                token_data = await response.json()
                access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)

                if access_token:
                    await cache_oauth_token(redis, access_token, expires_in)
                    logger.info("Successfully obtained and cached OAuth token")
                    return access_token
                else:
                    logger.error("No access token in OAuth response")
                    return None

    except Exception as e:
        logger.error(f"Error getting OAuth token: {e}")
        return None


async def send_chat_message(
    user_profile: str,
    last_messages: list[dict],
    message: str,
) -> ChatAnswer:
    """
    Sends a chat message to the chat service and returns the response.
    """
    last_messages = [{"role": "system", "content": user_profile}, *last_messages]

    # Consider sanitizing sensitive data before logging
    logger.info(f"Sending chat message with {len(last_messages)} previous messages")

    # Get OAuth token if configured
    redis = await get_redis_client()
    access_token = await get_oauth_token(redis)
    response = None
    try:
        async with aiohttp.ClientSession() as session:
            # Build payload according to new API format
            payload = {
                "question": message,
                "skip_knowledge_base": True,
                "history": last_messages
            }

            # Build headers
            headers = {"Content-Type": "application/json"}

            # Add OAuth headers if token is available
            if access_token and oauth_enabled():
                headers["Authorization"] = f"Bearer {access_token}"
                headers["Ocp-Apim-Subscription-Key"] = settings.CHAT_OAUTH_SUBSCRIPTION_KEY
                headers["Ocp-Apim-Trace"] = "true"
                logger.info("Using OAuth authentication for chat request")
            else:
                logger.info("Making chat request without OAuth authentication")

            logger.info(f"Payload for chat service: {payload}")

            async with session.post(CHAT_ENDPOINT, json=payload, headers=headers) as response:
                logger.info(f"Chat service response status: {response.status}")

                if response.status == 401 and access_token:
                    # Token might be expired, try to refresh
                    logger.info("Received 401, attempting to refresh OAuth token")
                    # Clear cached token
                    try:
                        await redis.delete(OAUTH_REDIS_KEY)
                    except:
                        pass

                    # Get new token and retry once
                    new_token = await get_oauth_token(redis)
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        headers["Ocp-Apim-Subscription-Key"] = settings.CHAT_OAUTH_SUBSCRIPTION_KEY
                        headers["Ocp-Apim-Trace"] = "true"
                        async with session.post(
                            CHAT_ENDPOINT, json=payload, headers=headers
                        ) as retry_response:
                            if retry_response.status != 200:
                                error_text = await retry_response.text()
                                raise ChatServiceError(
                                    f"Chat service returned {retry_response.status}: {error_text}"
                                )
                            response = retry_response
                    else:
                        error_text = await response.text()
                        raise ChatServiceError(f"Chat service returned {response.status}: {error_text}")

                elif response.status != 200:
                    error_text = await response.text()
                    raise ChatServiceError(f"Chat service returned {response.status}: {error_text}")

                try:
                    data = await response.json()
                except ContentTypeError as e:
                    raise ChatServiceError(f"Invalid JSON response: {e}")

                logger.info(f"Chat response received successfully: {data}")
                answer_text = data.get("answer", "")
                response = parse_message(answer_text)

    except ClientError as e:
        raise ChatServiceError(f"Network error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in send_chat_message: {e}")
        raise
    finally:
        await redis.close()
    return response
