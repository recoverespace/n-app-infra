from datetime import datetime, timedelta
import json
import asyncio
import random

from httpx import AsyncClient

from api.chat import collect_user_profile
from api.lib.chat_api import send_chat_message
from api.lib.tests.urls import CHATS, USERS_ME
from api.lib.tests.utils import add_fact, add_message, init_chat, init_user
from data.domain.llm.schemas import LLMDataSchema

FACTS = [
    {
        "kind": "food-logging",
        "label": "food-logging",
        "value": '{"options":["Snack"],"notes":"","extraInfo":"{\\"feeling\\":\\"stressed\\",\\"description\\":\\"Печеньки 3\\"}","date":"2025-07-13T08:00:33.765Z"}',
    },
    {
        "kind": "movement-checkin",
        "label": "movement-checkin",
        "value": '{"options":["yes"],"notes":"😔","extraInfo":"{\\"activityType\\":\\"walking\\"}","date":"2025-08-12T01:47:17.844Z"}',
    },
    {"kind": "eat-9", "label": "eat-9", "value": '{"options":["9"],"notes":"","extraInfo":""}'},
    {
        "kind": "social-connection-checkin",
        "label": "social-connection-checkin",
        "value": '{"options":["work-study"],"notes":"My job","extraInfo":"","date":"2025-09-04T03:39:21.020Z"}',
    },
    {"kind": "meal_plan_response", "label": "vomit", "value": "vomit"},
    {
        "kind": "doom-scrolling-checkin",
        "label": "doom-scrolling-checkin",
        "value": '{"options":["yes"],"notes":"binged the whole day. Too tired to do anything else\\n","extraInfo":"{\\"description\\":\\"Star wars, Modern Family, Transformers \\"}","date":"2025-08-02T22:43:52.656Z"}',
    },
    {
        "kind": "binge-eating",
        "label": "binge-eating",
        "value": '{"options":["yes"],"notes":"Я доела все сладкое что купила ","extraInfo":"{\\"intensity\\":\\"moderate\\"}","date":"2025-07-13T17:01:46.753Z"}',
    },
    {
        "kind": "vitamins-supplements-checkin",
        "label": "vitamins-supplements-checkin",
        "value": '{"options":["yes"],"notes":"😒","extraInfo":"","date":"2025-08-12T01:46:41.634Z"}',
    },
    {
        "kind": "mental-rest-checkin",
        "label": "mental-rest-checkin",
        "value": '{"options":["walked-moved"],"notes":"went on a walk and it was nice","extraInfo":"","date":"2025-09-03T07:18:06.464Z"}',
    },
    {
        "kind": "alcohol-checkin",
        "label": "alcohol-checkin",
        "value": '{"options":["yes"],"notes":"was really drunk and wasted","extraInfo":"{\\"hadBinge\\":\\"\\",\\"description\\":\\"a looooottt\\"}","date":"2025-08-16T13:50:00.846Z"}',
    },
    {
        "kind": "emotion-checkin",
        "label": "emotion-checkin",
        "value": '{"options":["tired"],"notes":"tired in general bc i wanna sleep but i wont because i have food in my system and tired of all of this","extraInfo":"","date":"2025-07-31T19:26:14.538Z"}',
    },
    {
        "kind": "cycle",
        "label": "cycle",
        "value": '{"options":[["physicalSymptoms",["tender_breasts"]],["emotionalSymptoms",["mood_swings"]],["behavioralSymptoms",["poor_sleep"]],["dateStart","2025-08-26T04:20:00.000Z"],["dateEnd","2025-08-31T08:21:05.762Z"],["cycleLength",28]],"notes":"Bgvan saha","extraInfo":"{\\"physicalSymptoms\\":[\\"tender_breasts\\"],\\"emotionalSymptoms\\":[\\"mood_swings\\"],\\"behavioralSymptoms\\":[\\"poor_sleep\\"],\\"dateStart\\":\\"2025-08-26T04:20:00.000Z\\",\\"dateEnd\\":\\"2025-08-31T08:21:05.762Z\\",\\"cycleLength\\":28}","date":"2025-08-31T08:20:49.586Z"}',
    },
    {
        "kind": "habits-routines-checkin",
        "label": "habits-routines-checkin",
        "value": '{"options":["yoga"],"notes":"And classical stretch ","extraInfo":"","date":"2025-07-11T18:46:55.635Z"}',
    },
    {
        "kind": "stress-checkin",
        "label": "stress-checkin",
        "value": '{"options":["very-low"],"notes":"🤨","extraInfo":"","date":"2025-08-12T01:49:12.241Z"}',
    },
    {
        "kind": "water-checkin",
        "label": "water-checkin",
        "value": '{"options":["yes"],"notes":"😓","extraInfo":"","date":"2025-08-10T03:22:29.731Z"}',
    },
    {
        "kind": "meal_plan",
        "label": "ADDITIONAL_SPACE•   Morning snackADDITIONAL_SPACEsome strawberries \nADDITIONAL_SPACE•   LunchADDITIONAL_SPACE3 turkey slices \n10 chips \n1 granola bar\n",
        "value": "{}",
    },
    {
        "kind": "day-mood-checkin",
        "label": "day-mood-checkin",
        "value": '{"options":["yes"],"notes":"🛐","extraInfo":"","date":"2025-08-11T03:00:50.460Z"}',
    },
    {
        "kind": "energy-checkin",
        "label": "energy-checkin",
        "value": '{"options":["9/10"],"notes":"So k acha lg ra ","extraInfo":"","date":"2025-07-27T06:23:27.576Z"}',
    },
    {
        "kind": "journal",
        "label": "journal",
        "value": '{"options":[],"notes":"🛐","extraInfo":"","date":"2025-08-12T01:54:19.178Z"}',
    },
    {
        "kind": "sleep-checkin",
        "label": "sleep-checkin",
        "value": '{"options":["yes"],"notes":"🥱","extraInfo":"","date":"2025-08-12T01:49:31.420Z"}',
    },
    {"kind": "eating_attitude", "label": "veryHigh", "value": "9"},
    {"kind": "sos-action", "label": "sos-action", "value": '{"notes":"show-library-item"}'},
]


async def test_user_profile(client: AsyncClient, mocker):
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    user = await init_user(client)
    chat = await init_chat(client)
    for f in FACTS:
        await add_fact(
            client,
            user,
            kind=f["kind"],
            label=f["label"],
            value=f["value"],
            extra={},
            age_days=random.randint(0, 5),
        )
    await asyncio.sleep(1)
    await add_message(client, chat, "First message!")

    await asyncio.sleep(1)
    await add_fact(
        client,
        user,
        kind="energy-checkin",
        label="energy-checkin",
        value='{"options":["9/10"],"notes":"So k acha lg ra ","extraInfo":"","date":"2025-07-27T06:23:27.576Z"}',
    )
    await asyncio.sleep(1)
    await add_message(client, chat, "Hello!")
    await asyncio.sleep(1)
    llm_data, messages = await collect_user_profile(user.id, chat.id)
    assert llm_data.user.id == str(user.id)
    assert llm_data.model_dump_json()
    assert json.dumps(messages)


async def test_new_checkins(client: AsyncClient, mocker):
    mocker.patch("api.lib.centrifuge.centrifuge.publish", return_value=None)
    user = await init_user(client)
    chat = await init_chat(client)
    first_message_ts = datetime.fromisoformat("2025-07-10T10:00:00+00:00")
    first_message_part_2_ts = first_message_ts + timedelta(minutes=1)
    first_fact_ts = first_message_ts - timedelta(minutes=10)
    second_fact_ts = first_message_ts + timedelta(minutes=5)
    second_message_ts = second_fact_ts + timedelta(minutes=10)
    await add_fact(
        client,
        user,
        kind="food-logging",
        label="food-logging",
        value='{"options":["Snack"],"notes":"","extraInfo":"{\\"feeling\\":\\"stressed\\",\\"description\\":\\"Печеньки 3\\"}"}',
    )
    await add_message(client, chat, "First message!")

    await add_message(client, chat, "First message!")

    llm_data, messages = await collect_user_profile(user.id, chat.id)
    assert llm_data.user.id == str(user.id)
    assert len(messages) == 3, llm_data
    assert all(not c.is_new for c in llm_data.recent_checkins)

    await add_fact(
        client,
        user,
        kind="energy-checkin",
        label="energy-checkin",
        value='{"options":["9/10"],"notes":"So k acha lg ra ","extraInfo":"", "date":"'
        + datetime.now().isoformat()
        + 'Z"}',
    )
    await add_message(client, chat, "Second message!")
    llm_data_new, messages_new = await collect_user_profile(user.id, chat.id)
    assert llm_data_new.recent_checkins[-1].is_new is True
    assert len(messages_new) == 5, messages_new


async def test_chat_api(client: AsyncClient, mocker):
    user_profile = ""
    last_messages = []
    message = "Hello, I'm feeling unwell. I vomited twice today and feel very tired and want to kill myself."
    response = await send_chat_message(user_profile, last_messages, message)
    assert response.answer is not None, response.answer
    assert response.metadata is not None, response.metadata
    assert "risk_keywords" in response.metadata, response.metadata
    assert "intentions_or_insights" in response.metadata, response.metadata
    assert ["vomit" in risks for risks in response.metadata["risk_keywords"]]
    assert ["tired" in insights for insights in response.metadata["intentions_or_insights"]]
