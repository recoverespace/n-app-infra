from fastapi import APIRouter, status, HTTPException
from api.lib.deps import DBDep, UserIDDep
from sqlmodel import and_, col
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from data.domain.users.schemas import UserRead, UserSettingsModel, UserUpdate
from data.domain.users.schemas.user import UserSettingsCreate

router = APIRouter()


@router.get("/me", summary="Get the current user")
async def get_user_me(user_id=UserIDDep, db=DBDep) -> UserRead:
    user = await user_crud.get(
        and_(col(User.id) == user_id, col(User.is_active) == True, col(User.is_deleted) == False), db=db
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.delete("/me", summary="Delete current user", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_me(user_id=UserIDDep, db=DBDep):
    user = await user_crud.get(User.id == user_id, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user_crud.update(user, {"uid": f"r_{user.uid}", "is_deleted": True}, db=db)


@router.patch("/me", summary="Update current user", status_code=status.HTTP_204_NO_CONTENT)
async def patch_user_me(user_in: UserUpdate, user_id=UserIDDep, db=DBDep):
    user = await user_crud.get(User.id == user_id, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await user_crud.update(user, user_in, db=db)


@router.patch("/me/settings", summary="Update user's settings", status_code=status.HTTP_204_NO_CONTENT)
async def patch_user_me_settings(settings: UserSettingsCreate, user_id=UserIDDep, db=DBDep):
    settings_dict = settings.model_dump(exclude_unset=True, mode="json")
    if not settings_dict:
        return
    user = await user_crud.get(User.id == user_id, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    new_settings = user.settings.model_copy(update=settings_dict)
    await user_crud.update(user, {"settings": new_settings}, db=db)
