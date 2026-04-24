import json
from uuid import uuid4
from common.otel import get_logger
from datetime import datetime, UTC
from sqlmodel import col
from data.lib.db import SessionLocal
from api.lib.chat_api import send_chat_message, ChatAnswer
from api.lib.dialog import dialog_typing, dialog_response
from data.domain.chat_messages import ChatMessage, chat_message_crud
from data.domain.facts import user_fact_crud
from data.domain.facts.schemas import USER_FACT_KINDS
from data.domain.users import user_crud, User
from data.domain.llm.schemas import LLMDataSchema
from api.settings import settings


from common.processing.schemas.dialog import DialogResponseMessage

logger = get_logger(__name__)


async def try_update_user_metadata(user_id: int, metadata: dict):
    if not metadata:
        return
    try:
        async with SessionLocal() as db:  # type: ignore
            user = await user_crud.get(col(User.id) == user_id, db=db)
            if not user:
                logger.error(f"User {user_id} not found for metadata update.")
                return
            # {
            #     "timestamp": "2025-03-31T16:45:10Z",
            #     "session_type": "standard",
            #     "mood_tone": "not_detected",
            #     "themes_active": ["not_detected"],
            #     "risk_keywords": [],
            #     "triggers_mentioned": ["not_detected"],
            #     "clinical_boundary": "not_detected",
            #     "intentions_or_insights": "not_detected",
            #     "content_suggestions_shown": [],
            #     "prior_co ntext_summary": "not_detected",
            #     "session_summary": "not_detected"
            # }
            settings_dict = user.settings.model_dump(exclude_unset=True, mode="json")
            current_user_risk_flags = user.settings.risk_flags or []
            current_user_intent_flags = user.settings.intent_flags or []
            if "risk_keywords" in metadata and isinstance(metadata["risk_keywords"], list):
                for risk in metadata["risk_keywords"]:
                    if risk not in current_user_risk_flags and risk != "not_detected":
                        current_user_risk_flags.append(risk)
            if "intentions_or_insights" in metadata and isinstance(metadata["intentions_or_insights"], str):
                intent = metadata["intentions_or_insights"]
                if intent and intent != "not_detected" and intent not in current_user_intent_flags:
                    current_user_intent_flags.append(intent)
            settings_dict["risk_flags"] = current_user_risk_flags
            settings_dict["intent_flags"] = current_user_intent_flags
            await user_crud.update(user, {"settings": settings_dict}, db=db)
            logger.info(f"Updated metadata for user {user_id}: {metadata}")
    except Exception as e:
        logger.error(f"Error updating metadata for user {user_id}: {e}")


async def collect_user_profile(user_id: int, chat_id: int) -> (LLMDataSchema, list[dict]):
    metadata = {}
    last_messages = []
    metadata = {}
    user = None
    facts = []
    try:
        async with SessionLocal() as db:  # type: ignore
            try:
                user = await user_crud.get(col(User.id) == user_id, db=db)
            except Exception as e:
                logger.error(f"Error fetching user profile for user {user_id}: {e}")
                user = None

        async with SessionLocal() as db:  # type: ignore
            facts = await user_fact_crud.get_all_last_facts(
                user_id=user_id, limit=settings.CHAT_MAX_FACT_HISTORY, max_days=730, db=db
            )
            facts = list(facts)[::-1]

        async with SessionLocal() as db:  # type: ignore
            messages = await chat_message_crud.get_last(
                col(ChatMessage.chat_id) == chat_id, count=settings.CHAT_MAX_MESSAGE_HISTORY, db=db
            )
            for msg in messages:
                try:
                    if isinstance(msg, ChatMessage):
                        last_messages.append({"role": msg.role, "content": msg.text, "_ts": msg.created_at})
                        if msg.extra and "metadata" in msg.extra:
                            metadata.update(msg.extra["metadata"])
                    elif isinstance(msg, dict):
                        last_messages.append(
                            {
                                "role": msg.get("role", "user"),
                                "content": msg.get("text", ""),
                                "_ts": msg.get("created_at", None),
                            }
                        )
                        if "extra" in msg and isinstance(msg["extra"], dict) and "metadata" in msg["extra"]:
                            metadata.update(msg["extra"]["metadata"])
                except Exception as e:
                    logger.error(f"Error formatting message {msg.id} for chat {chat_id}: {e}")
                    continue
                # Reverse messages to have oldest first
            last_messages = last_messages[::-1]
    except Exception as e:
        logger.error(f"Error processing chat message for user {user_id} in chat {chat_id}: {e}")
        return
    last_message_ts = last_messages[-2]["_ts"] if len(last_messages) > 1 else datetime.fromisoformat("1970-01-01T00:00:00+00:00")
    logger.info(f"Last message: {last_message_ts.isoformat()}")
    llm_data = LLMDataSchema.create(user, facts, last_message=last_message_ts) if user else None

    # Add system message for recent 5 checkins into last_messages
    new_last_messages = []
    checks_to_add = llm_data.recent_checkins[:5] if llm_data and llm_data.recent_checkins else []
    for msg in last_messages:
        msg_time = msg.get("_ts", None)
        while checks_to_add and checks_to_add[0].created_at and msg_time and msg_time >= checks_to_add[0].created_at:
            check = checks_to_add.pop(0)
            check_content = (
                f"User check-in: {json.dumps(check.model_dump(mode='json'), indent=2, default=str)}"
            )
            new_last_messages.append({"role": "system", "content": check_content})

        new_last_messages.append({"role": msg["role"], "content": msg["content"]})
    return llm_data, new_last_messages


async def process_chat_message(user_id: int, chat_id: int, message: str = ""):
    logger.info(f"Processing chat message for user {user_id} in chat {chat_id}: {message}")
    if not message:
        logger.info("Empty message received, skipping processing.")
        return
    await dialog_typing(chat_id, user_id, is_typing=True)
    try:
        llm_data, last_messages = await collect_user_profile(user_id, chat_id)
        logger.info(f"Processing chat message for user {user_id} in chat {chat_id}: {message}")
        user_profile = llm_data.model_dump_json() if llm_data else ""
        answer = await send_chat_message(user_profile, last_messages, message)
    except Exception as e:
        logger.error(f"Error sending chat message for user {user_id} in chat {chat_id}: {e}")
        await dialog_typing(chat_id, user_id, is_typing=False)
        return
    logger.info(f"Received response from chat service: {answer}")
    chat_message = ChatMessage(
        id=uuid4(),
        chat_id=chat_id,
        user_id=user_id,
        role="assistant",
        text=answer.answer,
        extra={"metadata": answer.metadata, "ai_suggestion": answer.suggestions},
        created_at=datetime.now(tz=UTC),
    )
    await dialog_response(
        DialogResponseMessage(
            user_id=user_id,
            chat_id=chat_id,
            original_message_id=0,
            items=[chat_message],
        )
    )
    await dialog_typing(chat_id, user_id, is_typing=False)
    if answer.metadata:
        await try_update_user_metadata(user_id, answer.metadata)
