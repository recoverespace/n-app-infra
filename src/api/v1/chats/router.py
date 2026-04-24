from fastapi import APIRouter
from .chat import router as chat_router
from .messages import router as messages_router
from .message_actions import router as message_actions_router

router = APIRouter(prefix="/chats")
router.include_router(chat_router, tags=["Chats"])
router.include_router(messages_router, tags=["Chats/Messages"])
router.include_router(message_actions_router, tags=["Chats/Actions"])
