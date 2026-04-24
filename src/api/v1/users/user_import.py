from dataclasses import dataclass

from data.domain.users.models import User
from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from api.lib.deps import DBDep

from common.otel import get_logger
from api.lib.gsheets import load_data as load_recovered_data, import_user as import_recovered_user
from api.lib.fell2heal import import_user as import_fell2heal_user, load_data as load_fell2heal_data

router = APIRouter()


logger = get_logger(__name__)


@dataclass
class UserImportRequest:
    email: str


async def try_load_recovered(email: str, data: UserImportRequest, db=DBDep) -> User | None:
    email = email.lower().strip()
    logger.info(f"Trying to load recovered user with email: {email}")
    data = load_recovered_data(email)
    if not data:
        return None
    user = await import_recovered_user(data, db)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Error creating user")


async def try_load_feel2heal(email: str, data: UserImportRequest, db=DBDep) -> User | None:
    email = email.lower().strip()
    logger.info(f"Trying to load feel2heal user with email: {email}")
    data = load_fell2heal_data(email)
    if not data:
        return None
    user = await import_fell2heal_user(data, db)
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Error creating user")


@router.post("/import", summary="Import form data using email")
async def get_user_me(data: UserImportRequest, db=DBDep):
    email = data.email.lower().strip()
    try:
        user = await try_load_recovered(email, data, db)
        if user:
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"message": "User created", "uid": user.uid}
            )
    except HTTPException as e:
        if e.status_code != status.HTTP_409_CONFLICT:
            return JSONResponse(status_code=e.status_code, content={"message": str(e.detail)})

    try:
        user = await try_load_feel2heal(email, data, db)
        if user:
            return JSONResponse(
                status_code=status.HTTP_200_OK, content={"message": "User created", "uid": user.uid}
            )
    except HTTPException as e:
        if e.status_code != status.HTTP_409_CONFLICT:
            return JSONResponse(status_code=e.status_code, content={"message": str(e.detail)})
