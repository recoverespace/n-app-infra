import json
import random
from uuid import uuid4
from enum import StrEnum
from common.otel import get_logger
from datetime import datetime, UTC
from data.domain.facts.schemas import UserFactCreate
from sqlmodel import all_, col
from asyncio import sleep
from data.lib.db import SessionLocal
from api.lib.dialog import dialog_typing, dialog_response, dialog_message_delete
from data.domain.chats import chat_crud, Chat
from data.domain.chat_messages import ChatMessage, chat_message_crud
from data.domain.intents.state import ChatState, ProactivityContext
from data.domain.chat_messages.schemas.message import Extra, ExtraAction, ExtraData, ExtraProactivity
from data.domain.chat_messages.schemas.suggestions import Suggestions, Suggestion
from data.domain.chat_messages.schemas.attachments import (
    AttachmentType,
    EatTestAttachment,
    EmotionsAttachment,
    ImageAttachment,
    EnergyResultAttachment,
    VideoAttachment,
)
from data.domain.facts import user_fact_crud, UserFact
from data.domain.users import user_crud, User


from common.processing.schemas.dialog import DialogResponseMessage

logger = get_logger(__name__)


class QAYesNo(StrEnum):
    Yes = "Yes"
    No = "No"


class QAPeriod(StrEnum):
    FewTimePerMonth = "2-3_times_a_month"
    FewTimePerWeek = "2-6_times_a_week"
    Never = "never"
    OncePerDay = "once_a_day"
    OncePerMonth = "once_a_month"
    OncePerWeek = "once_a_week"


async def typing_delay():
    await sleep(random.randrange(10, 30) / 10.0)


QA_CHECK = {
    "question-first": {
        False: [QAPeriod.Never, QAPeriod.OncePerMonth],
        True: [QAPeriod.FewTimePerMonth, QAPeriod.FewTimePerWeek, QAPeriod.OncePerDay, QAPeriod.OncePerWeek],
    },
    "question-second": {
        False: [QAPeriod.Never],
        True: [
            QAPeriod.OncePerMonth,
            QAPeriod.FewTimePerMonth,
            QAPeriod.FewTimePerWeek,
            QAPeriod.OncePerDay,
            QAPeriod.OncePerWeek,
        ],
    },
    "question-third": {
        False: [QAPeriod.Never],
        True: [
            QAPeriod.OncePerMonth,
            QAPeriod.FewTimePerMonth,
            QAPeriod.FewTimePerWeek,
            QAPeriod.OncePerDay,
            QAPeriod.OncePerWeek,
        ],
    },
    "question-fourth": {
        False: [
            QAPeriod.Never,
            QAPeriod.OncePerMonth,
            QAPeriod.FewTimePerMonth,
            QAPeriod.FewTimePerWeek,
            QAPeriod.OncePerWeek,
        ],
        True: [
            QAPeriod.OncePerDay,
        ],
    },
    "question-fifth": {False: [QAYesNo.No], True: [QAYesNo.Yes]},
    "question-six": {False: [QAYesNo.No], True: [QAYesNo.Yes]},
}

GREETING_TEXT = """
Hi there! Fantastic work! We've got your results ready. Your unique story matters to us, and we're committed to supporting you with personalized care.
"""
GREETING_TEXT_FOR_MIGRATED = "Hi there! We’re so glad you’re here, welcome to Recovered 😊"
GREETING_TEXT_FOR_MIGRATED_2 = "It looks like you've taken the EAT-26 before. 🎉 \n\nHere's a quick summary of your results: \nYour total EAT-26 score: {eat_26_score} \nYour eating disorder risk is {disorder_risk}"
GREETING_ATTENTION_NEEDED_TEXT = "‘It seems that some of the behaviors you've mentioned may require closer attention 🤗  Even when facing challenges with maladaptive  behaviors, understanding their root causes is crucial. That's why we're here to support you 🌞"
GREETING_TEST_MIGRATION_TEXT = "To make progress tracking easier for you, we’ve converted your EAT-26 score to the more concise EAT-9, created by Dr. David Garner, Ph.D.\n\nYou can find your EAT-9 score in the Tracker section 📊"
GREETING_NO_INDICATORS = (
    "There don’t appear to be any behaviors associated with severe eating disorders in your responses. That’s a positive sign!🌞"
)
GREETING_TEST_TEXT = "Let's explore eating attitude to make your recovery tailored!"
GREETING_FIRST_STEPS_TEXT = "Let's take this first step together. Awareness is key to healing, so we encourage you to explore our content library with resources created by Dr. Garner. If you have suggestions for more content, please email us. 🙏"
GREETING_TEST_SUGGESTIONS = [
    Suggestion(label="I want to explore my eating attitude", value="start_test"),
]
GREETING_IMAGE = ImageAttachment(
    url="https://api.recoveredspace.com/v1/chats/1/media/static/greeting.jpg",
    size={"width": 870, "height": 804},
)

TEST_START_TEXT = "Great! Let's start. 🌟 Check a response for each of the following statements:"
CANCEL_TEXT = "If you're not ready to take the test now, no worries! You can always return when you feel up to it. We highly recommend it to better taileor tour recovery"
CANCEL_SUGGESTION_TEXT = "Meanwhile, explore our expert-guided content with David Garner, PhD, to start your recovery journey"

TEST_PROMPT_LESS_THAN_WEEK_MESSAGE_TEXT = "It's great you're keep going and it's inspiring how motivated you are!"

TEST_PROMPT_LESS_THAN_WEEK_SECOND_TEXT = "In a few days you will be ready to take eating attitude test to see how you progress"

TEST_PROMPT_MESSAGE_TEXT = "It's time to check your current state. Let's take the eating attitude test together! We are here for you!"
TEST_PROMPT_SUGGESTIONS = [
    Suggestion(label="Yes", value="start_test"),
    Suggestion(label="No", value="cancel"),
]
TEST_SUGGESTION_MESSAGE_TEXT = ""
TEST_SUGGESTION_SUGGESTIONS = [
    Suggestion(label="I want to explore my eating attitude", value="start_test"),
]

RETURN_LESS_THAN_WEEK_IMAGE = ImageAttachment(
    url="https://api.recoveredspace.com/v1/chats/1/media/static/flowers.jpg",
    size={"width": 870, "height": 804},
)

CONGRATULATIONS_TEXT = "Congrats, you've completed the questionnaire! Your bravery and willingness to share inspire us 🌟"
RESULTS_TEXTS = {
    "low": "Approximately 43% of a non-clinical sample and only 6% of a sample of ED patients score less than 4 on the EAT- 9. Even though this is “low risk” it is important to remember that some ED patients score in this range, so a low score does not mean that you have no risk.",
    "mild": "Approximately 60% of a non-clinical sample and 15% of ED patients score 7 or less on the EAT-9. Even though this is “mild risk” it is important to remember that some ED patients score in this range, so a “mild risk” score does not mean that you have no risk.",
    "moderate": "Approximately 75% of a non-clinical sample and 30% of ED patients score 12 or less on the EAT-9. Even though this is “moderate risk” it is important to remember that a significant proportion of ED patients score in this range. It means that you likely have some eating problems that deserve attention.",
    "high": "Approximately 85% of a non-clinical sample and 50% of ED patients score 17 or less on the EAT-9. A very significant proportion of ED patients score in this range, so a high-risk score means that you have considerable risk of having serious eating problems.",
    "veryHigh": "Approximately 15% of a non-clinical sample and 50% of ED patients score above 14 on the EAT-9. A very significant proportion of ED patients score in this range, so a very high-risk score means that you have considerable risk of having serious eating problems.",
}


MEAL_PLAN_CHECK_CHEERS = [
    "We're sorry you're having a tough time. 🌱 Next time you feel an urge arise, check out the 'Emergency Kit' in our library. It’s filled with guides and tips to support you whenever you need them",
    "We understand this can be challenging. 🥗 When planning meals, try to include a variety of foods that you enjoy—balance helps keep you energized and satisfied.",
    "We understand it's not easy. When you feel an urge coming on, try to pause and take a deep breath. Find a distraction—a short walk, music, calling a friend, or simply shaking your body to release tension. You've got this. 🌿",
    "We're sorry to hear you're struggling. When planning meals, make sure they don’t feel like dieting. Aim for balance and satisfaction—restricting can lead to stronger urges later. 🌸",
    "It’s okay to have difficult moments. If an urge arises, take a few minutes to journal your emotions. Reflection can help shift your focus. 📝 Check out journaling tips in our library.",
    "We know how hard this can be. 💛 Think of your meal plan as self-care. Balanced meals that you enjoy and that provide enough energy can support your journey toward feeling better.",
    "We’re here for you. 🌸 Practice self-compassion when the urge arises. A quick meditation can help ground you—find guided meditations in our library.",
    "We're sorry you're struggling. 🌿 Remember to plan meals that leave you feeling satisfied. Balanced, nourishing meals can make a big difference in managing urges.",
    "We know it’s not easy. 🌱 When planning your meals, aim for balance—include foods that you enjoy and that fuel your body. It’s about nourishment, not restriction.",
    "We understand you may be going through a tough time. 🌿 When planning meals, check in with yourself: Are these meals enough to fuel your day and leave you feeling good? Balance is key.",
]


async def greetings(user_id: int, chat_id: int):
    logger.info(f"Generating greeting for user {user_id} in chat {chat_id}")
    attention_needed = False
    is_migrated_user = False
    try:
        async with SessionLocal() as db:  # type: ignore
            user = await user_crud.get(col(User.id) == user_id, db=db)
            qa = user.settings.questions_answers
            checks = []
            for qa_k, qa_v in qa.items():
                for k, v in QA_CHECK.get(qa_k, {}).items():
                    if qa_v in v:
                        checks.append(k)
            attention_needed = all(checks)
            is_migrated_user = user.settings.is_migrated_user
    except Exception as e:
        logger.warning(f"Failed to get user {user_id} data: {str(e)}")

    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    if is_migrated_user:
        message = ChatMessage(user_id=None, chat_id=chat_id, text=GREETING_TEXT_FOR_MIGRATED.strip())
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    else:
        message = ChatMessage(user_id=None, chat_id=chat_id, text=GREETING_TEXT.strip())
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        message = ChatMessage(user_id=None, chat_id=chat_id, text="", attachments=[GREETING_IMAGE])
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))

    await dialog_typing(chat_id, user_id, is_typing=False)


async def greetings_v2(user_id: int, chat_id: int):
    logger.info(f"Generating greeting for user {user_id} in chat {chat_id}")
    attention_needed = False
    is_migrated_user = False
    try:
        async with SessionLocal() as db:  # type: ignore
            user = await user_crud.get(col(User.id) == user_id, db=db)
            qa = user.settings.questions_answers
            checks = []
            for qa_k, qa_v in qa.items():
                for k, v in QA_CHECK.get(qa_k, {}).items():
                    if qa_v in v:
                        checks.append(k)
            attention_needed = all(checks)
            is_migrated_user = user.settings.is_migrated_user
    except Exception as e:
        logger.warning(f"Failed to get user {user_id} data: {str(e)}")

    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    if is_migrated_user:
        message = ChatMessage(user_id=None, chat_id=chat_id, text=GREETING_TEXT_FOR_MIGRATED.strip())
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        fact = None
        await typing_delay()
        try:
            async with SessionLocal() as db:  # type: ignore
                fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="eating_attitude", db=db)
        except Exception as e:
            logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

        if fact:
            score = fact.value
            message = GREETING_TEXT_FOR_MIGRATED_2.format(eat_26_score=fact.extra.get("eat-26-score"), disorder_risk=fact.label)
            message = ChatMessage(user_id=None, chat_id=chat_id, text=message.strip())
            await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
            message = ChatMessage(
                user_id=None,
                chat_id=chat_id,
                text="",
                attachments=[EnergyResultAttachment(value=score)],
            )
            await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    else:
        message = ChatMessage(user_id=None, chat_id=chat_id, text=GREETING_TEXT.strip())
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        message = ChatMessage(user_id=None, chat_id=chat_id, text="", attachments=[GREETING_IMAGE])
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))

    await typing_delay()
    if is_migrated_user:
        text = GREETING_TEST_MIGRATION_TEXT
    elif attention_needed:
        text = GREETING_ATTENTION_NEEDED_TEXT
    else:
        text = GREETING_NO_INDICATORS
    message = ChatMessage(user_id=None, chat_id=chat_id, text=text.strip())
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))

    await typing_delay()
    if is_migrated_user:
        await book_call_first_suggest(user_id, chat_id)
    else:
        message_test = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=GREETING_TEST_TEXT,
            suggestions=Suggestions(values=GREETING_TEST_SUGGESTIONS),
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message_test]))
    await dialog_typing(chat_id, user_id, is_typing=False)


async def cancel_test(user_id: int, chat_id: int):
    logger.info(f"Cancelled test for user {user_id} in chat {chat_id}")
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=CANCEL_TEXT,
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=CANCEL_SUGGESTION_TEXT,
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    await dialog_typing(chat_id, user_id, is_typing=False)


async def test_suggestions(user_id: int, chat_id: int):
    logger.info(f"Test suggestions prompt for user {user_id} in chat {chat_id}")
    await dialog_typing(chat_id, user_id, is_typing=True)

    try:
        proactivity = None
        async with SessionLocal() as db:  # type: ignore
            last_message = await chat_message_crud.get_last(col(ChatMessage.chat_id) == chat_id, count=3, db=db)
            for message in last_message:
                if message is not None and message.extra.proactivity is not None:
                    if message.extra.proactivity.state == "start":
                        proactivity_id = message.extra.proactivity.id
                        proactivity = ExtraProactivity(id=proactivity_id, kind="eat-test", state="end")
                    break

    except Exception as e:
        logger.warning(f"Failed to delete last message for chat={chat_id} data: {str(e)}")

    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=TEST_SUGGESTION_MESSAGE_TEXT,
        suggestions=Suggestions(values=TEST_SUGGESTION_SUGGESTIONS),
        extra=Extra(proactivity=proactivity),
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    await dialog_typing(chat_id, user_id, is_typing=False)


async def test_prompt(user_id: int, chat_id: int):
    logger.info(f"Test prompt for user {user_id} in chat {chat_id}")
    week_passed = False
    try:
        async with SessionLocal() as db:  # type: ignore
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="eating_attitude", db=db)
            if fact and fact.created_at:
                week_passed = (datetime.now(UTC) - fact.created_at).days >= 7
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")
    if not week_passed:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=TEST_PROMPT_LESS_THAN_WEEK_MESSAGE_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            attachments=[RETURN_LESS_THAN_WEEK_IMAGE],
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=TEST_PROMPT_LESS_THAN_WEEK_SECOND_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await dialog_typing(chat_id, user_id, is_typing=False)

    else:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=TEST_PROMPT_MESSAGE_TEXT,
            suggestions=Suggestions(values=TEST_PROMPT_SUGGESTIONS),
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await dialog_typing(chat_id, user_id, is_typing=False)


async def test_propose(user_id: int, chat_id: int, skip_check: bool = False):
    logger.info(f"Proposing test for user {user_id} in chat {chat_id}")

    week_passed = True
    try:
        async with SessionLocal() as db:  # type: ignore
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="eating_attitude", db=db)
            if fact and fact.created_at:
                week_passed = (fact.created_at - datetime.now(UTC)).days >= 7
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not week_passed and not skip_check:
        return
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=TEST_PROMPT_MESSAGE_TEXT,
        suggestions=Suggestions(values=TEST_PROMPT_SUGGESTIONS),
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    await dialog_typing(chat_id, user_id, is_typing=False)


async def test_start(user_id: int, chat_id: int, skip_check: bool = False):
    logger.info(f"Starting test for user {user_id} in chat {chat_id}")

    week_passed = True
    try:
        async with SessionLocal() as db:  # type: ignore
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="eating_attitude", db=db)
            if fact and fact.created_at:
                week_passed = (datetime.now(UTC) - fact.created_at).days >= 7
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not week_passed and not skip_check:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=TEST_PROMPT_LESS_THAN_WEEK_MESSAGE_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            attachments=[RETURN_LESS_THAN_WEEK_IMAGE],
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=TEST_PROMPT_LESS_THAN_WEEK_SECOND_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await dialog_typing(chat_id, user_id, is_typing=False)
        return

    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    proactivity_id = uuid4().hex
    async with SessionLocal() as db:  # type: ignore
        chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
        await chat_crud.update(
            chat,
            {"state": ChatState(proactivity=ProactivityContext(id=proactivity_id, kind="eat-test"))},
            db=db,
        )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=TEST_START_TEXT,
        extra=Extra(proactivity=ExtraProactivity(id=proactivity_id, kind="eat-test", state="start")),
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
    await dialog_typing(chat_id, user_id, is_typing=False)
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="",
        attachments=[EatTestAttachment()],
    )
    await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))


async def test_end(user_id: int, chat_id: int, value: str):
    logger.info(f"Ending test for user {user_id} in chat {chat_id}")
    first_test = False
    migrated_user = False
    if value and value.strip() != "-1":
        try:
            score = int(value.strip())
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
            async with SessionLocal() as db:  # type: ignore
                fact_date = datetime.now()
                logger.info(f"Saving user fact {user_id} data: {value} {level}")
                fact = await user_fact_crud.create(
                    UserFactCreate(
                        user_id=user_id,
                        kind="eating_attitude",
                        value=value,
                        label=level,
                        created_at=fact_date,
                    ),
                    db=db,
                )
                logger.info(f"Updating user {user_id} last eat test date")
                user = await user_crud.get(col(User.id) == user_id, db=db)
                migrated_user = user.settings.is_migrated_user
                if user.settings.lastEatTestDate is None:
                    logger.info(f"First test for user {user_id}")
                    first_test = True
                new_settings = user.settings.model_copy(update={"lastEatTestDate": fact_date})
                await user_crud.update(user, {"settings": new_settings}, db=db)
        except ValueError as e:
            logger.warning(f"Failed to parse score {value}: {str(e)}")
            score = 25
        except Exception as e:
            logger.warning(f"Failed to save user fact {user_id} data: {str(e)}")

        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CONGRATULATIONS_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            attachments=[EnergyResultAttachment(value=score)],
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        proactivity_id = uuid4().hex
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
            proactivity_id = chat.state.proactivity.id
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=RESULTS_TEXTS[level],
            extra=Extra(
                proactivity=ExtraProactivity(id=proactivity_id, kind="eat-test", state="end"),
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)

        await meal_plan_video(user_id, chat_id)
    else:
        proactivity_id = uuid4().hex
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
            proactivity_id = chat.state.proactivity.id
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            extra=Extra(
                proactivity=ExtraProactivity(id=proactivity_id, kind="eat-test", state="end"),
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CANCEL_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CANCEL_SUGGESTION_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await dialog_typing(chat_id, user_id, is_typing=False)


async def test_end_v2(user_id: int, chat_id: int, value: str):
    logger.info(f"Ending test for user {user_id} in chat {chat_id}")
    first_test = False
    migrated_user = False
    if value and value.strip() != "-1":
        try:
            score = int(value.strip())
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
            async with SessionLocal() as db:  # type: ignore
                fact_date = datetime.now()
                logger.info(f"Saving user fact {user_id} data: {value} {level}")
                fact = await user_fact_crud.create(
                    UserFactCreate(
                        user_id=user_id,
                        kind="eating_attitude",
                        value=value,
                        label=level,
                        created_at=fact_date,
                    ),
                    db=db,
                )
                logger.info(f"Updating user {user_id} last eat test date")
                user = await user_crud.get(col(User.id) == user_id, db=db)
                migrated_user = user.settings.is_migrated_user
                if user.settings.lastEatTestDate is None:
                    logger.info(f"First test for user {user_id}")
                    first_test = True
                new_settings = user.settings.model_copy(update={"lastEatTestDate": fact_date})
                await user_crud.update(user, {"settings": new_settings}, db=db)
        except ValueError as e:
            logger.warning(f"Failed to parse score {value}: {str(e)}")
            score = 25
        except Exception as e:
            logger.warning(f"Failed to save user fact {user_id} data: {str(e)}")

        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CONGRATULATIONS_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            attachments=[EnergyResultAttachment(value=score)],
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        proactivity_id = uuid4().hex
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
            proactivity_id = chat.state.proactivity.id
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=RESULTS_TEXTS[level],
            extra=Extra(
                proactivity=ExtraProactivity(id=proactivity_id, kind="eat-test", state="end"),
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)

        async with SessionLocal() as db:  # type: ignore
            user = await user_crud.get(col(User.id) == user_id, db=db)
            current_meal_plan_video = user.settings.current_meal_plan_video

            if current_meal_plan_video == 0:
                await book_call_first_suggest(user_id, chat_id)
            else:
                await meal_plan_video(user_id, chat_id)

    else:
        proactivity_id = uuid4().hex
        async with SessionLocal() as db:  # type: ignore
            chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
            proactivity_id = chat.state.proactivity.id
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="",
            extra=Extra(
                proactivity=ExtraProactivity(id=proactivity_id, kind="eat-test", state="end"),
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CANCEL_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=CANCEL_SUGGESTION_TEXT,
        )
        await dialog_response(DialogResponseMessage(user_id=user_id, chat_id=chat_id, original_message_id=0, items=[message]))
        await dialog_typing(chat_id, user_id, is_typing=False)


async def content(user_id: int, chat_id: int, value: str):
    logger.info(f"Pushing content message to user {user_id} in chat {chat_id}")
    if value and value.strip() == "":
        logger.warn("No value provided")
        return
    id, text = value.strip().split("||")
    async with SessionLocal() as db:  # type: ignore
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=text,
            extra=Extra(
                actions=[
                    ExtraAction(
                        kind="navigation",
                        data=ExtraData(label="Check out now", screen="library-item", params={"item-id": id}),
                    )
                ],
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )


async def meal_plan_suggest_video(user_id: int, chat_id: int):
    current_message = 1
    async with SessionLocal() as db:  # type: ignore
        user = await user_crud.get(col(User.id) == user_id, db=db)
        current_message = user.settings.current_meal_plan_video
    if current_message == 1:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="Take a moment to watch the video above and set yourself up for a successful recovery journey. You deserve this step forward! Once you've finished, press 'Next key insight' to continue.",
            suggestions=Suggestions(
                values=[
                    Suggestion(label="Next key insight", value="trigger:meal_plan_video:increment"),
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)

    if current_message == 2:
        await dialog_typing(chat_id, user_id, is_typing=True)

        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="Before you start creating your first meal plan, we strongly recommend watching the video above. It will be instrumental in setting you up for meal planning success. Once you've finished, press 'Done' to continue to meal planning.",
            suggestions=Suggestions(
                values=[
                    Suggestion(label="Done", value="trigger:meal_plan_video:final"),
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)


async def book_call_first_suggest(user_id: int, chat_id: int, value: str = ""):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Not sure what your score means? \n\nBook a free 15-minute private call with our recovery coach — confidential and supportive, to help you understand what it means and what to do next.",
        suggestions=Suggestions(
            values=[
                Suggestion(label="Not right now", value="trigger:book_call_third_suggest:"),
                Suggestion(label="Book a call", value="trigger:book_call_second_suggest:"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def book_call_second_suggest(user_id: int, chat_id: int, value: str = ""):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="You made it to the calendar — that's already a strong step. \n\nIf you didn’t finish booking your free 15-minute call, no worries — you can still grab a spot. And if you’d rather take some time to explore first, that’s totally fine too.",
        suggestions=Suggestions(
            values=[
                Suggestion(label="Continue exploring", value="trigger:join_community_suggest:"),
                Suggestion(label="Book a call", value="trigger:join_community_suggest:"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def book_call_third_suggest(user_id: int, chat_id: int, value: str = ""):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Totally understand — but it’s a shame to miss the chance to talk it through. \n\nIf you change your mind, our recovery coach is still here for you — just one click away.",
        suggestions=Suggestions(
            values=[
                Suggestion(label="No, I’m fine — I want to explore on my own", value="trigger:join_community_suggest:"),
                Suggestion(label="Book a call", value="trigger:join_community_suggest:"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def join_community_suggest(user_id: int, chat_id: int, value: str = ""):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Ever feel like you have no one to talk to? \n\nWe've got you. Join our private recovery community — a safe space to connect with others who really get it. \n\nNo judgment. Just support.",
        suggestions=Suggestions(
            values=[
                Suggestion(label="No, thanks", value="trigger:meal_plan_video:"),
                Suggestion(label="Join the community", value="trigger:meal_plan_video:"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_video(user_id: int, chat_id: int, value: str = ""):
    current_message = 1
    async with SessionLocal() as db:  # type: ignore
        user = await user_crud.get(col(User.id) == user_id, db=db)
        current_message = user.settings.current_meal_plan_video
        if current_message == 0:
            current_message = 1
        if value == "increment":
            current_message += 1
        if value == "final":
            current_message += 1
            user.settings.has_watched_meal_plan_video = True
        user.settings.current_meal_plan_video = current_message
        await user_crud.update(user, {"settings": user.settings.model_dump()}, db=db)
    if current_message == 1:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="Now hear from Dr. David Garner , PhD — the expert behind Recovered. Watch the video explaining you the basics of recovery. It takes only five minutes and the video has subtitles so you can watch it without sound.",
            attachments=[
                VideoAttachment(
                    url="https://player.vimeo.com/progressive_redirect/playback/1015375254/rendition/720p/file.mp4?loc=external&signature=3edc117e3c3385e2d274705e02a750fe21de62229dbce72beb84955153e0bf73"
                )
            ],
            suggestions=Suggestions(
                values=[
                    Suggestion(label="Next key insight", value="trigger:meal_plan_video:increment"),
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)

    if current_message == 2:
        await dialog_typing(chat_id, user_id, is_typing=True)

        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="You’re on the right track! 🎉 Learn how meal planning can transform your recovery with Dr. Garner. He’ll show you how to use it effectively and share key tips and principles to create a meal plan that works for you. The video is only 3 minutes long and has subtitles so you can watch it without sound.",
            attachments=[
                VideoAttachment(
                    url="https://player.vimeo.com/progressive_redirect/playback/1015376967/rendition/720p/file.mp4?loc=external&signature=13fbf2ae5ade4b276402b943175e6c68197d752e6ec3ed4d60fbd977f0a9ecd6"
                )
            ],
            suggestions=Suggestions(
                values=[
                    Suggestion(label="Done", value="trigger:meal_plan_video:final"),
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)

    if current_message > 2:
        await dialog_typing(chat_id, user_id, is_typing=True)
        await typing_delay()
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="Now, when you read these materials and understand the importance of logging and planning, you have to start doing it, and we are here to provide you with very simple tools for this.",
            extra=Extra(
                actions=[
                    ExtraAction(
                        kind="navigation",
                        data=ExtraData(
                            label="Start meal planning",
                            screen="meal-planning",
                        ),
                    )
                ],
                data={"is_last_meal_plan_video": True},
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
        await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_update(user_id: int, chat_id: int, value: str | None = None):
    meal_plan = None
    meal_plan_text = ""
    if value:
        try:
            meal_plan = json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to parse meal plan data: {str(e)}")
    try:
        async with SessionLocal() as db:  # type: ignore
            for k, v in meal_plan.items():
                meal_plan_text += f"ADDITIONAL_SPACE•   {k.replace('-', ' ').capitalize()}ADDITIONAL_SPACE{v}"
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="meal_plan", db=db)
            fact.value = value
            fact.label = meal_plan_text
            fact.extra = meal_plan
            await user_fact_crud.update(fact, fact.model_dump(), db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not meal_plan:
        return

    message = ChatMessage(
        user_id=user_id,
        chat_id=chat_id,
        text="I have updated my meal plan",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=f"This is your meal plan:{meal_plan_text}",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )


async def meal_plan_edit(user_id: int, chat_id: int, value: str | None = None):
    meal_plan = None
    meal_plan_text = ""
    if value:
        try:
            meal_plan = json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to parse meal plan data: {str(e)}")
    try:
        async with SessionLocal() as db:  # type: ignore
            for k, v in meal_plan.items():
                meal_plan_text += f"ADDITIONAL_SPACE•   {k.replace('-', ' ').capitalize()}ADDITIONAL_SPACE{v}"
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="meal_plan", db=db)
            fact.value = value
            fact.label = meal_plan_text
            fact.extra = meal_plan
            await user_fact_crud.update(fact, fact.model_dump(), db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not meal_plan:
        return

    message = ChatMessage(
        user_id=user_id,
        chat_id=chat_id,
        text="I have updated my meal plan",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=f"This is your meal plan:{meal_plan_text}",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Is your list complete?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="No, Edit", value="meal_plan_incomplete"),
                Suggestion(label="Yes, Save", value="trigger:meal_plan_submission_finish:"),
            ]
        ),
        extra=Extra(data=fact.model_dump()),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_submission(user_id: int, chat_id: int, value: str | None = None):
    meal_plan = None
    meal_plan_text = ""
    meal_plan_counter = 0
    if value:
        try:
            meal_plan = json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to parse meal plan data: {str(e)}")
    try:
        async with SessionLocal() as db:  # type: ignore
            for k, v in meal_plan.items():
                meal_plan_text += f"ADDITIONAL_SPACE•   {k.replace('-', ' ').capitalize()}ADDITIONAL_SPACE{v}"
            fact = await user_fact_crud.create(
                UserFactCreate(
                    user_id=user_id,
                    kind="meal_plan",
                    value=value,
                    label=meal_plan_text,
                    extra=meal_plan,
                    created_at=datetime.now(UTC),
                ),
                db=db,
            )

            user = await user_crud.get(col(User.id) == user_id, db=db)
            meal_plan_counter = user.settings.meal_plan_counter + 1
            new_settings = user.settings.model_copy(
                update={"last_meal_planning_date": datetime.now(UTC), "meal_plan_counter": meal_plan_counter}
            )
            await user_crud.update(user, {"settings": new_settings}, db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not meal_plan:
        return
    message = ChatMessage(
        user_id=user_id,
        chat_id=chat_id,
        text="I’m done with planning",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    motivational_messages = [
        "You’re crushing it with your meal planning 😊. Keep up the amazing work! We’ll catch up tonight to review your progress. You’ve totally got this!",  # noqa: E501, RUF001
        "Fantastic job getting your meals organized 😊. You’re doing great! Let’s reconnect later to see how it’s going. You’re unstoppable!",  # noqa: E501, RUF001
        "Meal planning like a pro 😊! So proud of you. Let’s meet in the evening and go over your plan. You’ve got this under control!",  # noqa: E501, RUF001
        "You are rocking with your meal planning 😊. Absolutely amazing! See you this evening to check in on everything. You’re on fire!",  # noqa: E501, RUF001
        "Awesome job planning your meals 😊. You’re on point! Let’s touch base tonight and see how it’s going. You’re totally nailing it!",  # noqa: E501, RUF001
        "You’re doing an incredible job with meal planning 😊. You’re a superstar! Let’s regroup later to see how it’s coming along. You’ve got this!",  # noqa: E501, RUF001
        "Way to go with your meal planning 😊! You’re amazing! We’ll check in this evening and make sure everything’s on track. You’ve got this!",  # noqa: E501, RUF001
        "Your meal planning game is strong 😊. Well done! Let’s meet back here tonight to review your progress. You’re going to ace it!",  # noqa: E501, RUF001
        "You’re absolutely rocking this meal plan 😊. Keep being awesome! Let’s catch up later to see how everything’s going. You’ve got this!",  # noqa: E501, RUF001
        "Super job on organizing your meals 😊. You’re fantastic! Let’s meet up this evening and check on your plan. You’ve got this in the bag!",  # noqa: E501, RUF001
    ]
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=random.choice(motivational_messages),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    proactivity_id = uuid4().hex
    async with SessionLocal() as db:  # type: ignore
        chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
        await chat_crud.update(
            chat,
            {"state": ChatState(proactivity=ProactivityContext(id=proactivity_id, kind="meal-plan"))},
            db=db,
        )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=f"This is your meal plan:{meal_plan_text}",
        extra=Extra(
            proactivity=ExtraProactivity(id=proactivity_id, kind="meal-plan", state="start"),
            data={"date": datetime.now(UTC).date().isoformat()},
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Is your list complete?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="No, Edit", value="meal_plan_incomplete"),
                Suggestion(label="Yes, Save", value="trigger:meal_plan_submission_finish:"),
            ]
        ),
        extra=Extra(data=fact.model_dump()),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_submission_v2(user_id: int, chat_id: int, value: str | None = None):
    meal_plan = None
    meal_plan_text = ""
    meal_plan_counter = 0
    if value:
        try:
            meal_plan = json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to parse meal plan data: {str(e)}")
    try:
        async with SessionLocal() as db:  # type: ignore
            for k, v in meal_plan.items():
                meal_plan_text += f"ADDITIONAL_SPACE•   {k.replace('-', ' ').capitalize()}ADDITIONAL_SPACE{v}"
            fact = await user_fact_crud.create(
                UserFactCreate(
                    user_id=user_id,
                    kind="meal_plan",
                    value=value,
                    label=meal_plan_text,
                    extra=meal_plan,
                    created_at=datetime.now(UTC),
                ),
                db=db,
            )

            user = await user_crud.get(col(User.id) == user_id, db=db)
            meal_plan_counter = user.settings.meal_plan_counter + 1
            new_settings = user.settings.model_copy(
                update={"last_meal_planning_date": datetime.now(UTC), "meal_plan_counter": meal_plan_counter}
            )
            await user_crud.update(user, {"settings": new_settings}, db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not meal_plan:
        return
    message = ChatMessage(
        user_id=user_id,
        chat_id=chat_id,
        text="I’m done with planning",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    motivational_messages = [
        "You’re crushing it with your meal planning 😊. Keep up the amazing work! We’ll catch up tonight to review your progress. You’ve totally got this!",  # noqa: E501, RUF001
        "Fantastic job getting your meals organized 😊. You’re doing great! Let’s reconnect later to see how it’s going. You’re unstoppable!",  # noqa: E501, RUF001
        "Meal planning like a pro 😊! So proud of you. Let’s meet in the evening and go over your plan. You’ve got this under control!",  # noqa: E501, RUF001
        "You are rocking with your meal planning 😊. Absolutely amazing! See you this evening to check in on everything. You’re on fire!",  # noqa: E501, RUF001
        "Awesome job planning your meals 😊. You’re on point! Let’s touch base tonight and see how it’s going. You’re totally nailing it!",  # noqa: E501, RUF001
        "You’re doing an incredible job with meal planning 😊. You’re a superstar! Let’s regroup later to see how it’s coming along. You’ve got this!",  # noqa: E501, RUF001
        "Way to go with your meal planning 😊! You’re amazing! We’ll check in this evening and make sure everything’s on track. You’ve got this!",  # noqa: E501, RUF001
        "Your meal planning game is strong 😊. Well done! Let’s meet back here tonight to review your progress. You’re going to ace it!",  # noqa: E501, RUF001
        "You’re absolutely rocking this meal plan 😊. Keep being awesome! Let’s catch up later to see how everything’s going. You’ve got this!",  # noqa: E501, RUF001
        "Super job on organizing your meals 😊. You’re fantastic! Let’s meet up this evening and check on your plan. You’ve got this in the bag!",  # noqa: E501, RUF001
    ]
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=random.choice(motivational_messages),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    proactivity_id = uuid4().hex
    async with SessionLocal() as db:  # type: ignore
        chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
        await chat_crud.update(
            chat,
            {"state": ChatState(proactivity=ProactivityContext(id=proactivity_id, kind="meal-plan"))},
            db=db,
        )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=f"This is your meal plan:{meal_plan_text}",
        extra=Extra(
            proactivity=ExtraProactivity(id=proactivity_id, kind="meal-plan", state="start"),
            data={"date": datetime.now(UTC).date().isoformat()},
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Is your list complete?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="No, Edit", value="meal_plan_incomplete"),
                Suggestion(label="Yes, Save", value="trigger:meal_plan_submission_finish:"),
            ]
        ),
        extra=Extra(data=fact.model_dump()),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_submission_finish(user_id: int, chat_id: int, value: str | None = None):
    proactivity_id = uuid4().hex
    async with SessionLocal() as db:  # type: ignore
        chat = await chat_crud.get(col(Chat.id) == chat_id, db=db)
        proactivity_id = chat.state.proactivity.id
    await dialog_typing(chat_id, user_id, is_typing=True)
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        extra=Extra(proactivity=ExtraProactivity(id=proactivity_id, kind="meal-plan", state="end")),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)

    meal_plan_counter = -1
    async with SessionLocal() as db:  # type: ignore
        user = await user_crud.get(col(User.id) == user_id, db=db)
        meal_plan_counter = user.settings.meal_plan_counter

    if meal_plan_counter == 1:
        # Trigger app refresher after the first meal plan submission
        await app_refresher(user_id, chat_id)


async def meal_plan_check_submission(user_id: int, chat_id: int, value: str | None = None):
    meal_plan = None
    meal_plan_text = ""
    if not value:
        logger.warning("Failed to get meal plan data")
        return
    if value:
        try:
            meal_plan = json.loads(value)
        except Exception as e:
            logger.warning(f"Failed to parse meal plan data: {str(e)}")
    try:
        async with SessionLocal() as db:  # type: ignore
            for k, v in meal_plan.items():
                meal_plan_text += f"ADDITIONAL_SPACE•   {k.replace('-', ' ').capitalize()}ADDITIONAL_SPACE{v}"
            last_fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="meal_plan", db=db)
            if last_fact:
                await user_fact_crud.update(last_fact, {"extra": meal_plan, "created_at": datetime.now(UTC)}, db=db)
            else:
                fact = await user_fact_crud.create(
                    UserFactCreate(
                        user_id=user_id,
                        kind="meal_plan",
                        value=value,
                        label=meal_plan_text,
                        extra=meal_plan,
                        created_at=datetime.now(UTC),
                    ),
                    db=db,
                )
            user = await user_crud.get(col(User.id) == user_id, db=db)
            new_settings = user.settings.model_copy(update={"last_meal_planning_check_date": datetime.now(UTC)})
            await user_crud.update(user, {"settings": new_settings}, db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    message = ChatMessage(
        user_id=user_id,
        chat_id=chat_id,
        text="I have updated my meal plan",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Thank you! You are awesome!",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text=f"Here's what you've eaten:{meal_plan_text}",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await typing_delay()

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Did you binge?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="Yes", value="trigger:binge_trigger:yes"),
                Suggestion(label="No", value="trigger:binge_trigger:no"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def binge_trigger(user_id: int, chat_id: int, value: str | None = None):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()

    if value == "yes":
        async with SessionLocal() as db:  # type: ignore
            await user_fact_crud.create(
                UserFactCreate(
                    user_id=user_id,
                    kind="meal_plan_response",
                    value="binge",
                    label="binge",
                    created_at=datetime.now(),
                ),
                db=db,
            )

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Did you vomit?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="Yes", value=f"trigger:vomit_trigger:{value}_yes"),
                Suggestion(label="No", value=f"trigger:vomit_trigger:{value}_no"),
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def vomit_trigger(user_id: int, chat_id: int, value: str | None = None):
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()
    async with SessionLocal() as db:  # type: ignore
        if value.split("_")[-1] == "yes":
            logger.info(f"Saving user fact {user_id} data: vomit")
            await user_fact_crud.create(
                UserFactCreate(
                    user_id=user_id,
                    kind="meal_plan_response",
                    value="vomit",
                    label="vomit",
                    created_at=datetime.now(),
                ),
                db=db,
            )
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="How are you feeling?",
        suggestions=Suggestions(
            values=[
                Suggestion(label="🙁 sad", value=f"trigger:meal_plan_response:{value}_sad"),
                Suggestion(label="😌 calm", value=f"trigger:meal_plan_response:{value}_calm"),
                Suggestion(label="🙂 happy", value=f"trigger:meal_plan_response:{value}_happy"),
                Suggestion(label="🤩 energetic", value=f"trigger:meal_plan_response:{value}_energetic"),
                Suggestion(label="😣 irritated", value=f"trigger:meal_plan_response:{value}_irritated"),
                Suggestion(label="😜 frisky", value=f"trigger:meal_plan_response:{value}_frisky"),
                Suggestion(label="😕 mood swings", value=f"trigger:meal_plan_response:{value}_mood-swings"),  # noqa: E501
                Suggestion(label="😔 feeling guilty", value=f"trigger:meal_plan_response:{value}_feeling-guilty"),  # noqa: E501
                Suggestion(label="🙁 depressed", value=f"trigger:meal_plan_response:{value}_depressed"),
                Suggestion(label="😓 anxious", value=f"trigger:meal_plan_response:{value}_anxious"),
                Suggestion(label="🥱 low energy", value=f"trigger:meal_plan_response:{value}_low-energy"),
                Suggestion(label="😶 apathetic", value=f"trigger:meal_plan_response:{value}_apathetic"),
                Suggestion(label="😧 confused", value=f"trigger:meal_plan_response:{value}_confused"),
                Suggestion(
                    label="🤯 obsessive thoughts",
                    value=f"trigger:meal_plan_response:{value}_obsessive-thoughts",
                ),  # noqa: E501
                Suggestion(
                    label="🧐 very self-critical",
                    value=f"trigger:meal_plan_response:{value}_very-self-critical",
                ),  # noqa: E501
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_response(user_id: int, chat_id: int, value: str | None = None):
    # value would be in format `{binge_yes/no}_{vomit_yes/no}_{emotion}`
    # emotion could be empty, but the hanging `_` should be always there
    if value:
        binge, vomit, emotion = value.split("_")
        async with SessionLocal() as db:  # type: ignore
            if emotion:
                await user_fact_crud.create(
                    UserFactCreate(
                        user_id=user_id,
                        kind="meal_plan_response",
                        value=emotion,
                        label=emotion,
                        created_at=datetime.now(),
                    ),
                    db=db,
                )
    if binge == "no" and vomit == "no":
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="Thank you! You are doing great!",
            extra=Extra(
                actions=[
                    ExtraAction(
                        kind="navigation",
                        data=ExtraData(
                            label="Set up your meal",
                            screen="meal-planning",
                        ),
                    )
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )
    else:
        index = 0

        async with SessionLocal() as db:  # type: ignore
            user = await user_crud.get(col(User.id) == user_id, db=db)
            index = user.settings.meal_plan_cheer_index
            new_settings = user.settings.model_copy(
                update={"meal_plan_cheer_index": index + 1 if index + 1 < len(MEAL_PLAN_CHECK_CHEERS) else 0}
            )
            await user_crud.update(user, {"settings": new_settings}, db=db)

        cheer_message = MEAL_PLAN_CHECK_CHEERS[index]
        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text=cheer_message,
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )

        message = ChatMessage(
            user_id=None,
            chat_id=chat_id,
            text="To help bring some structure to your day, let’s take a step forward and create your meal plan🌼",
            extra=Extra(
                actions=[
                    ExtraAction(
                        kind="navigation",
                        data=ExtraData(
                            label="Plan meals",
                            screen="meal-planning",
                        ),
                    )
                ]
            ),
        )
        await dialog_response(
            DialogResponseMessage(
                user_id=user_id,
                chat_id=chat_id,
                original_message_id=0,
                items=[message],
            )
        )


async def meal_plan_check(user_id: int, chat_id: int):
    fact = None
    try:
        async with SessionLocal() as db:  # type: ignore
            fact = await user_fact_crud.get_last_fact(user_id=user_id, kind="meal_plan", db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not fact:
        return
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Welcome back 👐Let’s reflect on how your meals went",
        extra=Extra(
            actions=[
                ExtraAction(
                    kind="navigation",
                    data=ExtraData(label="Review your plan", screen="review-meal-planning", params=fact.model_dump()),
                )
            ]
        ),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


async def meal_plan_submission_error(user_id: int, chat_id: int):
    fact = None
    try:
        async with SessionLocal() as db:  # type: ignore
            fact = await user_fact_crud.get_last_fact(user_id, kind="meal_plan", db=db)
    except Exception as e:
        logger.warning(f"Failed to get user fact {user_id} data: {str(e)}")

    if not fact:
        return
    await dialog_typing(chat_id, user_id, is_typing=True)
    await typing_delay()

    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)


#####


async def app_refresher(user_id: int, chat_id: int):
    await dialog_typing(chat_id, user_id, is_typing=True)
    proactivity_id = uuid4().hex

    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Now, let’s take a look around! 🔍",
        extra=Extra(proactivity=ExtraProactivity(id=proactivity_id, kind="refresher", state="start")),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )

    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Let’s start with the tracker! 📊\n\nEach week, you’ll be asked to complete an eating attitude test (just like in onboarding). Your results will appear in the tracker, so you can monitor your progress and see your improvement. You’ll find the tracker right in the bottom navigation bar ✅",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )

    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Our library section 📚 (bottom right corner) is filled with useful resources to support your journey.\n\nYou’ll find an Emergency Kit 🚨 for immediate help, insights and educational content to deepen your understanding, and a daily encouragement section for extra support.\n\nFor relaxation, there’s also a section with meditation tools available whenever you need them 🧘",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )

    await typing_delay()
    message = ChatMessage(
        user_id=None,
        chat_id=chat_id,
        text="Need a refresher? 🔄\n\nIf you ever need a reminder of how things work, you can always restart this walkthrough from the top-right menu.",
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)
