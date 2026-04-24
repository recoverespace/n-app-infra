from typing import Any
from fastapi import APIRouter, status
from common.otel import get_logger
from api.lib.push import push_segment_message
from api.lib.deps import RedisDep
from api.lib.storyblok import get_story_info, get_story_info_mapi

router = APIRouter(prefix="/storyblok")
logger = get_logger(__name__)


@router.post("", status_code=status.HTTP_201_CREATED)
async def notify(data: dict[str, Any], redis=RedisDep):
    logger.info(f"Storyblock notification: {data}")
    slug = str(data.get("full_slug", ""))
    if not slug.startswith("library/") or slug.count("/") < 2:
        return
    cache_key = f"storyblok_notified:{data.get('space_id', 0)}_{data.get('story_id', 0)}"
    value = await redis.get(cache_key)
    if value:
        logger.info("Notification for this content already sent")
        return

    await redis.set(cache_key, 1)
    story_id = data.get("story_id", "")
    story = None
    if story_id:
        story = await get_story_info_mapi(data.get("story_id", ""))
    if not story:
        story = await get_story_info(slug)

    await push_segment_message(
        segment="Active Subscriptions",
        title="📢 Fresh Insights Await!",
        url="recovered://library",
        template_id="46721e9b-3dfe-4e13-945c-a20336be5f15",
        extra={
            "story": story.name,
            "category": story.category,
            "type": story.type,
            "full_slug": story.full_slug,
        },
    )
