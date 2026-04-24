import os
import re
from uuid import uuid4
from datetime import datetime, timedelta
from dateutil.parser import parse

from data.domain.facts.models import UserFact
import gspread
from sqlmodel import and_, col
from sqlmodel.ext.asyncio.session import AsyncSession

from api.lib.firebase import check_firebase_user, create_firebase_user
from api.settings import settings
from api.utils import generate_username
from common.otel import get_logger
from data.domain.facts import UserFactCreate, user_fact_crud
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from data.domain.users.schemas import UserCreate, UserSettingsModel, UserUpdate

logger = get_logger(__name__)

col_mapping = [
    "question_1",  # "I often feel emotionally exhausted, even when nothing major has happened",
    "question_2",  # "I overthink or replay situations that upset me",
    "question_3",  # "My moods change without warning, and I don’t always understand why",
    "question_4",  # "I don’t know what helps me calm down when I’m triggered",
    "question_5",  # "I keep my feelings inside because I don’t want to seem too emotional",
    "question_6",  # "My sleep and energy are inconsistent",
    "question_7",  # "I avoid plans or people when I’m scared I won’t feel okay",
    "question_8",  # "I wish I had tools to manage stress and anxiety in a better way",
    "email",  # "Where should we send your results?",
    "",  # "bla bla ",
    "",  # "final_result_text",
    "",  # "high_score_res",
    "",  # "low_score_res",
    "",  # "moderate_score_res",
    "score",  # "score",
    "total_score",  # "total_score",
    "",  # "winning_outcome_id",
    "",  # "ending_displayed_id",
    "submitted_at",  # "Submitted at",
    "",  # "token"
]


def _try_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _convert_datetime(value: str) -> datetime | None:
    try:
        return parse(value)
    except ValueError:
        try:
            # Convert Excel-format date
            excel_start = datetime(1899, 12, 30)
            days, fraction = value.split(".")
            seconds = round(int(fraction) * 86400)
            return excel_start + timedelta(days=int(days), seconds=seconds)
        except ValueError:
            logger.error(f"Failed to parse date: {value}")
        return None


def load_data(filtered_email: str | None = None):
    if settings.GSPREAD_SERVICE_ACCOUNT_FILE != "":
        gc = gspread.service_account(filename=settings.GSPREAD_SERVICE_ACCOUNT_FILE)
    else:
        if not os.path.exists("/gspread.json"):
            with open("/gspread.json", "w") as f:
                f.write(settings.GSPREAD_SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account(filename="/gspread.json")
    sh = gc.open_by_url(settings.FEEL2HEAL_USERS_URL)
    ws = sh.worksheets()[0]
    list_of_dicts = ws.get_all_values()
    users = []
    for row in list_of_dicts[1:]:
        data = {}
        for i, col_name in enumerate(col_mapping):
            if col_name:
                data[col_name] = row[i]
        email = data.get("email").lower().strip()
        if email != "" and (filtered_email is None or email == filtered_email):
            users.append(data)
    return reversed(users)


def create_fact(user_id: int, created_at: datetime, user_data: dict[str, str]) -> UserFactCreate:
    score = user_data.get("total_score", "0")
    try:
        score = int(score)
    except ValueError:
        logger.warning(f"Invalid score value: {score} for user {user_id}")
        score = 0
    level = "low"
    if score < 5:
        level = "low"
    elif score < 8:
        level = "mild"
    elif score < 13:
        level = "moderate"
    elif score < 18:
        level = "high"
    else:
        level = "veryHigh"
    return UserFactCreate(
        user_id=user_id,
        kind="eating_attitude",
        label=level,
        value=str(score),
        extra={"eat-9-score": user_data.get("total_score", "0")},
        created_at=created_at,
        updated_at=created_at,
    )


async def import_user(data: list[dict[str, str]], db: AsyncSession) -> User | None:
    created_user = None
    for user_data in data:
        try:
            email = user_data.get("email").strip()
            logger.info(f"Importing user: {email} from {user_data}")
            uid = str(uuid4())
            fact_date = _convert_datetime(user_data.get("submitted_at", "")) or datetime(2024, 1, 1)
            display_name = generate_username()
            user_exists = await check_firebase_user(email)
            if not user_exists:
                logger.info(f"User {email} does not exist in Firebase. Creating...")
                await create_firebase_user(uid, display_name, email, "password")
            else:
                logger.info(f"User {email} already exists in Firebase")
                uid = user_exists

            settings = UserSettingsModel(
                age=_try_int(user_data.get("age", "")),
                lastEatTestDate=_convert_datetime(user_data.get("test_date", "")),
                is_onboarding_finished=True,
                notifications_enabled=False,
                questions_answers={},
                is_migrated_user=True,
                user_source="feel2heal",
            )
            logger.info(f"Parsed: {uid} - {display_name}, {settings}. Last fact date: {fact_date}")
            if not created_user:
                user = await user_crud.get_multi(
                    condition=and_(col(User.email).ilike(email), col(User.is_deleted).is_(False)),
                    db=db,
                )
                if user:
                    user = user[0]
                    if user.settings.is_migrated_user:
                        logger.info(f"User {email} already exists in DB and is migrated")
                    else:
                        logger.warning(f"User {email} already exists in DB, but not migrated")
                        user_update = UserUpdate(
                            id=user.id,
                            display_name=display_name,
                            settings=settings,
                            is_active=True,
                            is_deleted=False,
                        )
                        await user_crud.update(user, user_update, db=db)
                else:
                    user_create = UserCreate(
                        uid=uid,
                        email=email,
                        display_name=display_name,
                        settings=settings,
                        is_active=True,
                        is_deleted=False,
                    )
                    user = await user_crud.create(user_create, db=db)
                    created_user = user

            last_facts = await user_fact_crud.get_count_by(and_(UserFact.user_id == user.id, UserFact.created_at >= fact_date), db=db)
            if last_facts == 0:
                fact = create_fact(user_id=user.id, created_at=fact_date, user_data=user_data)
                try:
                    await user_fact_crud.create(fact, db=db)
                except Exception as e:
                    logger.warning(f"Failed to create fact for user {email}: {e}")
                logger.info(f"User {email} imported successfully")
            created_user = user
        except Exception as e:
            logger.error(f"Failed to import user {email}: {e}")
    return created_user


async def import_users(data: dict[str, dict[str, str]], log: list[str]) -> list[str]:
    created_emails = {}
    log = []
    for user_data in data:
        await import_user(user_data, log, created_emails)
    return log
