import asyncio
from datetime import UTC, datetime, timedelta

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlmodel import col

from api.lib.centrifuge import centrifuge
from api.settings import settings
from common.otel import get_logger, init_telemetry
from common.processing.schemas.dialog import DialogRunIntentRequest
from common.processing.streams import dialog_run_intent
from data.domain.chats import Chat, chat_crud
from data.domain.users import User, user_crud
from data.lib.db import SessionLocal
from api.lib.push import push_message
from redis.connection import parse_url

init_telemetry(f"{settings.SERVICE_PREFIX}-api-scheduler")
logger = get_logger(__name__)

jobstores = {"default": RedisJobStore(**parse_url(str(settings.REDIS_DSN)))}
executors = {"default": AsyncIOExecutor()}
job_defaults = {"coalesce": False, "max_instances": 10}
scheduler = AsyncIOScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=UTC
)


async def send_proactivity_to_user(user_id: int, proactivity_id: int, try_number: int = 0):
    logger.info(f"Sending proactivity {proactivity_id} to user {user_id}")
    user_present = await centrifuge.is_present(user_id)
    if user_present:
        # Skip sending message if user is present
        if try_number < 2:
            logger.info(f"User is present. Rescheduling {proactivity_id} to user {user_id}")
            scheduler.add_job(
                send_proactivity_to_user,
                args=[user_id, proactivity_id, try_number + 1],
                trigger="date",
                run_date=datetime.now(UTC) + timedelta(minutes=10),
            )
        else:
            logger.info(f"User is present. Skipping {proactivity_id} to user {user_id} after 3 tries")
        return

    async with SessionLocal() as db:  # type: ignore
        logger.info(f"Sending proactivity {proactivity_id} to user {user_id}")


@scheduler.scheduled_job("cron", minute="55")
async def create_user_messages():
    async with SessionLocal() as db:  # type: ignore
        proactivities = []
        utc_time = (datetime.now(UTC) + timedelta(minutes=10)).replace(minute=0, second=0, microsecond=0)
        for proactivity in proactivities:
            users = await proactivity.get_users(utc_time, db)
            for user in users:
                scheduler.add_job(
                    send_proactivity_to_user,
                    args=[user.id, proactivity.id],
                    trigger="date",
                    run_date=utc_time,
                )


async def main():
    scheduler.start()
    while True:
        await asyncio.sleep(1000)


if __name__ == "__main__":
    asyncio.run(main())
