from fastapi import APIRouter
from .me import router as users_me_router
from .facts import router as facts
from .user_import import router as user_import_router

router = APIRouter(prefix="/users")
router.include_router(users_me_router, tags=["Users/Me"])
router.include_router(facts, tags=["Users/Me/Facts"])
router.include_router(user_import_router, tags=["Users/Import"])
