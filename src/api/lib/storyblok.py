from dataclasses import dataclass

import requests

from api.settings import settings
from common.otel import get_logger

logger = get_logger(__name__)
API_URL = "https://api.storyblok.com/v2/cdn"
MAPI_URL = "https://mapi.storyblok.com/v1/spaces/289135"


@dataclass
class StoryInfo:
    name: str
    slug: str
    full_slug: str
    category: str
    type: str


def _convert_category(category: str) -> str:
    match category:
        case "talk-it-out-expert-podcasts":
            return "Talk It Out: Expert Podcasts"
        case "cbt-toolbox":
            return "CBT Toolbox"
        case "insights-and-education":
            return "Insights and Education"
        case _:
            return category.replace("-", "  ").lower()


async def get_story_info_mapi(storyId: str) -> StoryInfo | None:
    url = f"{MAPI_URL}/stories/{storyId}"
    response = requests.get(url, headers={"Authorization": f"{settings.STORYBLOK_MAPI_TOKEN}"})
    data = response.json()
    logger.info(f"Storyblok response [{response.status_code}]: {data}")
    if not data or response.status_code != 200:
        return None
    story = data.get("story", {})
    return StoryInfo(
        name=story.get("name", ""),
        slug=story.get("slug", ""),
        full_slug=story.get("full_slug", ""),
        category=story.get("parent", {}).get("name", ""),
        type=story.get("content", {}).get("type", ""),
    )


async def get_story_info(full_slug: str) -> StoryInfo:
    url = f"{API_URL}/stories/{full_slug}?token={settings.STORYBLOK_TOKEN}"
    response = requests.get(url)
    data = response.json()
    logger.info(f"Storyblok response [{response.status_code}]: {data}")
    raw_category = full_slug.split("/")[1]
    temp_name = _convert_category(full_slug.split("/")[-1]).capitalize()
    if not data or response.status_code != 200:
        return StoryInfo(
            name=temp_name,
            slug=full_slug,
            full_slug=full_slug,
            category=_convert_category(raw_category),
            type="content",
        )
    story = data.get("story", {})
    return StoryInfo(
        name=story.get("name", ""),
        slug=story.get("slug", ""),
        full_slug=full_slug,
        category=_convert_category(raw_category),
        type=story.get("content", {}).get("type", ""),
    )
