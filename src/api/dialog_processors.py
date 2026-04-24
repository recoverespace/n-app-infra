from common.otel import get_logger
from common.processing.schemas.dialog import DialogActionMessage, DialogTriggerMessage, DialogMessage
from api.dialogs import (
    binge_trigger,
    greetings,
    greetings_v2,
    meal_plan_check,
    meal_plan_check_submission,
    meal_plan_submission,
    meal_plan_submission_v2,
    meal_plan_submission_error,
    meal_plan_submission_finish,
    meal_plan_update,
    meal_plan_edit,
    meal_plan_video,
    meal_plan_suggest_video,
    test_prompt,
    cancel_test,
    test_suggestions,
    test_propose,
    test_start,
    test_end,
    test_end_v2,
    content,
    vomit_trigger,
    meal_plan_response,
    app_refresher,
    book_call_first_suggest,
    book_call_second_suggest,
    book_call_third_suggest,
    join_community_suggest,
)
from api.chat import process_chat_message

logger = get_logger(__name__)


async def process_dialog_message(req: DialogActionMessage | DialogTriggerMessage):
    logger.info(f"Received dialog action: {req}")
    kind = req.kind.strip() if req.kind else None
    match kind:
        case "greetings":
            await greetings(user_id=req.user_id, chat_id=req.chat_id)
        case "greetings_v2":
            await greetings_v2(user_id=req.user_id, chat_id=req.chat_id)
        case "test_prompt":
            await test_prompt(user_id=req.user_id, chat_id=req.chat_id)
        case "test_suggestions":
            await test_suggestions(user_id=req.user_id, chat_id=req.chat_id)
        case "cancel_test":
            await cancel_test(user_id=req.user_id, chat_id=req.chat_id)
        case "test_propose":
            await test_propose(user_id=req.user_id, chat_id=req.chat_id, skip_check=True)
        case "test_start":
            await test_start(user_id=req.user_id, chat_id=req.chat_id, skip_check=False)
        case "test_end":
            await test_end(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "test_end_v2":
            await test_end_v2(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "content":
            await content(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_video":
            await meal_plan_video(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_suggest_video":
            await meal_plan_suggest_video(user_id=req.user_id, chat_id=req.chat_id)
        case "meal_plan_edit":
            await meal_plan_edit(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_submission_v2":
            await meal_plan_submission_v2(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_submission":
            await meal_plan_submission(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_update":
            await meal_plan_update(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_submission_error":
            await meal_plan_submission_error(user_id=req.user_id, chat_id=req.chat_id)
        case "app_refresher":
            await app_refresher(user_id=req.user_id, chat_id=req.chat_id)
        case "meal_plan_check":
            await meal_plan_check(user_id=req.user_id, chat_id=req.chat_id)
        case "meal_plan_check_submission":
            await meal_plan_check_submission(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_submission_finish":
            await meal_plan_submission_finish(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "binge_trigger":
            await binge_trigger(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "vomit_trigger":
            await vomit_trigger(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "meal_plan_response":
            await meal_plan_response(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "book_call_first_suggest":
            await book_call_first_suggest(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "book_call_second_suggest":
            await book_call_second_suggest(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "book_call_third_suggest":
            await book_call_third_suggest(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "join_community_suggest":
            await join_community_suggest(user_id=req.user_id, chat_id=req.chat_id, value=req.extra.get("value", ""))
        case "message":
            await process_chat_message(user_id=req.user_id, chat_id=req.chat_id, message=req.extra.get("value", ""))
        case _:
            pass
        # await dialog_action(req)
