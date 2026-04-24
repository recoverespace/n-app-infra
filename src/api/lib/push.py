from onesignal_sdk.client import AsyncClient
from onesignal_sdk.error import OneSignalHTTPError

from api.settings import settings
from common.otel import get_logger

logger = get_logger(__name__)


async def push_segment_message(
    segment: str,
    title: str,
    url: str,
    message: str | None = None,
    template_id: str | None = None,
    extra: dict[str, str] | None = None,
):
    if settings.ONESIGNAL_APP_ID == "" and settings.ONESIGNAL_DEV_APP_ID == "":
        logger.warning("OneSignal is not configured")

    client = AsyncClient(app_id=settings.ONESIGNAL_APP_ID, rest_api_key=settings.ONESIGNAL_API_KEY)
    if template_id is not None:
        notification_body = {
            "included_segments": [segment],
            "template_id": template_id,
            "data": extra if extra is not None else {},
            "custom_data": extra if extra is not None else {},
            "url": url,
        }
    else:
        notification_body = {
            "included_segments": [segment],
            "contents": {"en": message},
            "headings": {"en": title},
            "data": extra if extra is not None else {},
            "url": url,
        }
    try:
        logger.info(f"Sending push to clients {segment}")
        response = await client.send_notification(notification_body)
    except Exception as e:
        logger.exception(f"Error sending push messsage. {e} response={e.http_response.json()}")
        return False
    return True


async def push_message(
    user_uid: str,
    user_id: int,
    chat_id: int,
    message_id: int,
    text: str,
    is_tester: bool = False,
    collapse_id: str | None = None,
    extra: dict[str, str] | None = None,
    url: str = "recovered://chat",
):
    if settings.ONESIGNAL_APP_ID == "" and settings.ONESIGNAL_DEV_APP_ID == "":
        logger.warning("OneSignal is not configured")

    prod_client = AsyncClient(app_id=settings.ONESIGNAL_APP_ID, rest_api_key=settings.ONESIGNAL_API_KEY)
    dev_client = AsyncClient(
        app_id=settings.ONESIGNAL_DEV_APP_ID, rest_api_key=settings.ONESIGNAL_DEV_API_KEY
    )

    client = dev_client if is_tester else prod_client
    alt_client = prod_client if is_tester else dev_client
    test_tag = "[T]" if is_tester else ""
    custom_data = {"chat_id": chat_id, "message_id": message_id}
    if extra is not None:
        custom_data |= extra
    notification_body = {
        "contents": {"en": test_tag + text},
        "target_channel": "push",
        "collapse_id": f"{collapse_id}_{test_tag}",
        "include_aliases": {"external_id": [user_uid]},
        "data": custom_data,
        "url": url,
    }
    try:
        logger.info(f"Sending push to client {user_uid=}. Dev = {is_tester}")
        response = await client.send_notification(notification_body)
        logger.info(f"Push sent: {response.body=}")
    except Exception:
        try:
            logger.info(f"Sending push to alt client {user_uid=}. Dev = {is_tester}")
            response = await alt_client.send_notification(notification_body)
            logger.info(f"Push sent: {response.body=}")
        except Exception as e:
            logger.exception(
                "Error sending push messsage. {} response={}",
                e.__class__.__name__,
                e.http_response.json(),
            )
            return False
    return True
