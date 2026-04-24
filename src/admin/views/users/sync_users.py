import asyncio
import json
import gspread
import os
from datetime import datetime, timedelta
from functools import partial

import firebase_admin
from firebase_admin import auth, credentials
from sqladmin import BaseView, expose
from sqlmodel import and_
from wtforms import Form, StringField

from admin.settings import settings
from common.otel import get_logger
from data.domain.facts import UserFact, user_fact_crud
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from data.lib.db import SessionLocal

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

logger = get_logger(__name__)
firebase_initialized = False


async def init_firebase():
    global firebase_initialized
    if settings.FIREBASE_CERTIFICATE:
        try:
            firebase_cert = json.loads(settings.FIREBASE_CERTIFICATE)
            firebase_cert["private_key"] = firebase_cert.get("private_key", "").replace("\\n", "\n")
            firebase_admin.initialize_app(credential=credentials.Certificate(firebase_cert))
            firebase_initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")


async def check_user_exists(email: str) -> bool:
    global firebase_initialized
    if not firebase_initialized:
        await init_firebase()

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(auth.get_user_by_email, email=email),
        )
        return True
    except Exception as exc:
        logger.warning(f"Create user={email}. reason={str(exc)}")
    return False


async def firebase_delete_user(uid: str, email: str) -> bool:
    global firebase_initialized
    if not firebase_initialized:
        await init_firebase()

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(auth.delete_user, uid=uid),
        )
        logger.info(f"Deleted user user={email}")
        return True
    except Exception as exc:
        logger.warning("Deleted user={}. reason={}", email, repr(exc))
    return False


async def delete_users_from(url: str):
    if settings.GSPREAD_SERVICE_ACCOUNT_FILE != "":
        gc = gspread.service_account(filename=settings.GSPREAD_SERVICE_ACCOUNT_FILE)
    else:
        if not os.path.exists("/gspread.json"):
            with open("/gspread.json", "w") as f:
                f.write(settings.GSPREAD_SERVICE_ACCOUNT_JSON)
        gc = gspread.service_account(filename="/gspread.json")
    sh = gc.open_by_url(url)
    ws = sh.worksheets()[0]
    list_of_dicts = ws.get_all_values()
    users = []
    for row in list_of_dicts[1:]:
        data = {}
        for i, col_name in enumerate(col_mapping):
            if col_name:
                data[col_name] = row[i]
        if data["email"].strip() != "":
            email = data.get("email").strip()
            uid = data.get("typeform_id")
            await firebase_delete_user(uid, email)
            async with SessionLocal() as db:
                users = await user_crud.get_multi(condition=(User.email==email), db=db)
                try:
                    for user in users:
                        await user_fact_crud.remove_all(condition=and_(UserFact.user_id == user.id), db=db)
                except Exception as e:
                    logger.error(f"Failed to delete user facts: {e}")
                try:
                    await user_crud.remove_all(condition=and_(User.email == email), db=db)
                except Exception as e:
                    logger.error(f"Failed to delete user: {e}")
    return users


class SyncForm(Form):
    url = StringField("Sheet URL")


class SyncUsersView(BaseView):
    name = "Sync Users"
    category = "User Management"
    icon = ""

    @expose("/sync_users", methods=["GET"])
    async def sync_users_page(self, request):
        form = SyncForm(request.query_params)
        log = None
        request_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if request.query_params.get("save"):
            _ts = datetime.fromisoformat(request.query_params.get("request_ts"))
            if _ts < datetime.now() - timedelta(minutes=1):
                print("Request expired")
            else:
                log = "Starting import\n"
                if form.validate():
                    url = form.url.data
                    await delete_users_from(url)
                else:
                    log += "Form validation failed"

        return await self.templates.TemplateResponse(
            request, "sync_users.html", {"error": None, "form": form, "log": log, "request_ts": request_ts}
        )
