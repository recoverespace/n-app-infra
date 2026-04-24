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
    "typeform_id",  # "#",
    "gender",  # "What gender are you/were you assigned at birth?",
    "age",  # "What is your age?",
    "height",  # "What is your height ?",
    "weight",  # "What is your current weight ?",
    "eat-26-1",  # "I am terrified about being overweight",
    "eat-26-2",  # "I avoid eating when I'm hungry",
    "eat-26-3",  # "I find myself preoccupied with food",
    "eat-26-4",  # "I have gone on eating binges where I feel that I may not be able to stop",
    "eat-26-5",  # "I cut my food into small pieces",
    "eat-26-6",  # "I aware of the calorie content of foods that I eat",
    "eat-26-7",  # "I particularly avoid food with a high carbohydrate content (i.e. bread, rice, potatoes, etc.)\n",
    "eat-26-8",  # "I feel that others would prefer if I ate more",
    "eat-26-9",  # "I vomit after I have eaten",
    "eat-26-10",  # "I feel extremely guilty after eating",
    "eat-26-11",  # "I am occupied with a desire to be thinner",
    "eat-26-12",  # "I think about burning up calories when I exercise",
    "eat-26-13",  # "Other people think that I am too thin",
    "eat-26-14",  # "I am preoccupied with the thought of having fat on my body",
    "eat-26-15",  # "I take longer than others to eat my meals",
    "eat-26-16",  # "I avoid foods with sugar in them",
    "eat-26-17",  # "I eat diet foods",
    "eat-26-18",  # "I feel that food controls my life",
    "eat-26-19",  # "I display self-control around food",
    "eat-26-20",  # "I feel that others pressure me to eat",
    "eat-26-21",  # "I give too much time and thought to food",
    "eat-26-22",  # "I feel uncomfortable after eating sweets",
    "eat-26-23",  # "I engage in dieting behavior",
    "eat-26-24",  # "I like my stomach to be empty",
    "eat-26-25",  # "I have the impulse to vomit after meals",
    "eat-26-26",  # "I enjoy trying new rich foods",
    "eat-26-27",  # "I go on eating binges where I feel that I may not be able to stop",
    "eat-26-28",  # "I have made myself sick (vomited) to control my weight or shape?",
    "eat-26-29",  # "I use laxatives, diet pills or diuretics (water pills) to control my weight or shape",
    "eat-26-30",  # "I have exercised more than 60 minutes a day to lose or to control my weight",
    "eat-26-31",  # "I have lost 20 pounds or more in the past 6 months",
    "eat-26-32",  # "Have you ever been treated for an eating disorder? ",
    "nickname",  # "Let's pick a nickname for you",
    "email",  # "What is your email?",
    "",  # "age",
    "",  # "binge",
    "",  # "bmi",
    "",  # "bmi_res",
    "",  # "counter_33eee3fe_3250_44f4_b646_f00dc360c636",
    "",  # "email",
    "",  # "exercise",
    "",  # "fla_res",
    "",  # "flag",
    "",  # "gender",
    "",  # "height",
    "",  # "lax",
    "",  # "nickname",
    "",  # "previous_ed",
    "eat-26-score",  # "Score",
    "",  # "score_res",
    "",  # "vomit",
    "",  # "weight",
    "",  # "weightloss",
    "",  # "Ending",
    "",  # "Response Type",
    "",  # "Start Date (UTC)",
    "",  # "Stage Date (UTC)",
    "test_date",  # "Submit Date (UTC)",
    "",  # "Network ID",
    "",  # "Tags",
]


def _try_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _convert_gender(value: str) -> str:
    if value.lower() == "male":
        return "he-his"
    if value.lower() == "female":
        return "she-her"
    return "not-to-say"


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


def _convert_weight(weight) -> int | None:
    KG_IN_LB = 0.45359237

    # Define patterns to match
    lbs_pattern = re.compile(r"(\d+\.?\d*)\s*lbs", re.IGNORECASE)
    kg_pattern = re.compile(r"(\d+\.?\d*)\s*kg", re.IGNORECASE)
    just_number_pattern = re.compile(r"(\d+\.?\d*)$")

    # Check for different patterns
    if match := lbs_pattern.match(weight):
        lbs = float(match.group(1))
        return round(lbs * KG_IN_LB)
    elif match := kg_pattern.match(weight):
        return round(float(match.group(1)))
    elif match := just_number_pattern.match(weight):
        return round(float(match.group(1)))  # Assuming number without unit is in kg
    else:
        return None


def _convert_height(height: str) -> int | None:
    CM_IN_INCH = 2.54
    INCHES_IN_FOOT = 12
    ft_in_pattern = re.compile(r"(\d+)\s*ft\s*([\d.]*)\s*in", re.IGNORECASE)
    ft_in_pattern_2 = re.compile(r"(\d+)\s*’\s*([\d.]*)", re.IGNORECASE)
    ft_only_pattern = re.compile(r"(\d+)\s*ft", re.IGNORECASE)
    in_pattern = re.compile(r"(\d+)\s*in", re.IGNORECASE)
    cm_pattern = re.compile(r"([\d.]+)\s*cm*", re.IGNORECASE)
    meters_pattern = re.compile(r"(\d+\.\d+)$")
    just_number_pattern = re.compile(r"(\d+)$")

    # Check for different patterns
    if match := ft_in_pattern.match(height):
        feet = int(match.group(1))
        inches = float(match.group(2)) if match.group(2) else 0
        return round(feet * INCHES_IN_FOOT * CM_IN_INCH + inches * CM_IN_INCH)
    elif match := ft_in_pattern_2.match(height):
        feet = int(match.group(1))
        inches = float(match.group(2)) if match.group(2) else 0
        return round(feet * INCHES_IN_FOOT * CM_IN_INCH + inches * CM_IN_INCH)
    elif match := ft_only_pattern.match(height):
        feet = int(match.group(1))
        return round(feet * INCHES_IN_FOOT * CM_IN_INCH)
    elif match := in_pattern.match(height):
        inches = int(match.group(1))
        return round(inches * CM_IN_INCH)
    elif match := cm_pattern.match(height):
        return round(float(match.group(1)))
    elif match := meters_pattern.match(height):
        return round(float(match.group(1)) * 100)
    elif match := just_number_pattern.match(height):
        inches = int(match.group(1))
        return round(inches)
    else:
        return None


def load_data(filtered_email: str | None = None):
    if settings.GSPREAD_SERVICE_ACCOUNT_FILE != "":
        gc = gspread.service_account(filename=settings.GSPREAD_SERVICE_ACCOUNT_FILE)
    else:
        if not os.path.exists("/gspread.json"):
            with open("/gspread.json", "w") as f:
                f.write(settings.GSPREAD_SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account(filename="/gspread.json")
    sh = gc.open_by_url(settings.GSPREAD_USERS_URL)
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
    freq_mapping = {
        "always": 3,
        "usually": 2,
        "often": 1,
        "sometimes": 0,
        "rarely": 0,
        "never": 0,
    }
    binges_mapping = {
        "never": 3,
        "once per month or less": 3,
        "2-3 times per month": 2,
        "once a week": 2,
        "2-6 times per week": 0,
        "once a day or more": 0,
    }
    yesno_20_pounds_mapping = {
        "yes": 3,
        "no": 0,
    }
    questions = [
        "eat-26-1",
        "eat-26-3",
        "eat-26-9",
        "eat-26-11",
        "eat-26-18",
        "eat-26-14",
        "eat-26-21",
        "eat-26-25",
    ]
    score = 0
    has_data = False
    for q in questions:
        freq = user_data.get(q, "").lower()
        if freq in freq_mapping:
            has_data = True
            score += freq_mapping[freq]
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
    if not has_data:
        score = user_data.get("eat-26-score", "0")
    return UserFactCreate(
        user_id=user_id,
        kind="eating_attitude",
        label=level,
        value=str(score),
        extra={"eat-26-score": user_data.get("eat-26-score", "")},
        created_at=created_at,
        updated_at=created_at,
    )


async def import_user(data: list[dict[str, str]], db: AsyncSession) -> User | None:
    created_user = None
    for user_data in data:
        try:
            email = user_data.get("email").strip()
            logger.info(f"Importing user: {email} from {user_data}")

            uid = user_data.get("typeform_id")
            if not uid:
                uid = str(uuid4())
            display_name = user_data.get("nickname")
            fact_date = _convert_datetime(user_data.get("test_date", "")) or datetime(2024, 1, 1)
            if not display_name:
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
                gender=_convert_gender(user_data.get("gender", "")),
                height_cm=_convert_height(user_data.get("height", "")),
                lastEatTestDate=_convert_datetime(user_data.get("test_date", "")),
                is_onboarding_finished=True,
                notifications_enabled=False,
                questions_answers={},
                weight_kg=_convert_weight(user_data.get("weight", "")),
                is_migrated_user=True,
                user_source="recovered",
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
