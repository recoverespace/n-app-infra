import aiohttp

from api.settings import settings
from common.otel import get_logger


logger = get_logger(__name__)


class ResendError(RuntimeError):
    pass


async def resend_send_email(*, to: str, subject: str, html: str, text: str) -> str:
    """Send an email via Resend. Returns Resend message id on success."""
    if not settings.RESEND_API_KEY:
        raise ResendError("RESEND_API_KEY is not set")
    if not settings.RESEND_FROM:
        raise ResendError("RESEND_FROM is not set")

    url = "https://api.resend.com/emails"
    headers = {"Authorization": f"Bearer {settings.RESEND_API_KEY}", "Content-Type": "application/json"}
    payload: dict = {
        "from": settings.RESEND_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if settings.RESEND_REPLY_TO:
        payload["reply_to"] = [settings.RESEND_REPLY_TO]

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            body_text = await resp.text()
            if resp.status < 200 or resp.status >= 300:
                logger.error(f"Resend error status={resp.status} body={body_text}")
                raise ResendError(f"Resend failed with status {resp.status}")

            try:
                data = await resp.json()
            except Exception as exc:
                logger.error(f"Resend invalid json body={body_text}")
                raise ResendError("Resend returned invalid JSON") from exc

            message_id = data.get("id")
            if not message_id:
                logger.error(f"Resend success without id body={data}")
                raise ResendError("Resend response missing id")
            return str(message_id)

