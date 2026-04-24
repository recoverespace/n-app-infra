from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, and_
from pydantic import BaseModel
from datetime import datetime

from api.lib.circle import circle_service
from api.lib.deps import DBDep, UserIDDep
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from common.otel import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/circle", tags=["Circle"])


class CircleTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    community_member_id: int
    community_id: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    access_token: str
    access_token_expires_at: datetime


@router.post("/login", response_model=CircleTokenResponse)
async def circle_login(
    user_id: int = UserIDDep,
    db=DBDep,
) -> CircleTokenResponse:
    """
    Login with Circle.so using email.
    Returns:
    - 404 if user not found in our system
    - 422 if user not found in Circle.so
    - 401 if Circle.so authentication failed
    - 500 if Circle.so integration is not available or other errors
    """

    user = await user_crud.get(
        and_(
            col(User.id) == user_id,
            col(User.is_active).is_(True),
            col(User.is_deleted).is_(False),
        ),
        db=db,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        response = await circle_service.get_token(user.email)
        logger.info(f"Successfully logged in to Circle.so for user {user_id}")
        return CircleTokenResponse(**response)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during Circle.so login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Circle.so login",
        )


@router.post("/connect", response_model=CircleTokenResponse)
async def create_circle_user(
    user_id: int = UserIDDep,
    db=DBDep,
) -> CircleTokenResponse:
    """
    Create a Circle.so user for an authenticated user and return Circle.so tokens.
    This endpoint requires a valid JWT token in the Authorization header.
    """
    user = await user_crud.get(
        and_(
            col(User.id) == user_id,
            col(User.is_active).is_(True),
            col(User.is_deleted).is_(False),
        ),
        db=db,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User email is required for Circle.so integration",
        )

    try:
        await circle_service.create_member_for_user(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
        )

        response = await circle_service.get_token(user.email)
        logger.info(f"Successfully connected user {user_id} to Circle.so")
        return CircleTokenResponse(**response)
    except Exception as e:
        logger.error(f"Failed to create Circle.so member: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create Circle.so member",
        )


@router.post("/token/refresh", response_model=RefreshTokenResponse)
async def refresh_circle_token(
    request: RefreshTokenRequest,
) -> RefreshTokenResponse:
    """
    Refresh Circle.so access token using a refresh token.
    Returns:
    - 401 if refresh token is expired
    - 404 if refresh token not found
    - 422 if token generation failed
    - 500 if Circle.so integration is not available or other errors
    """
    try:
        response = await circle_service.refresh_token(request.refresh_token)
        logger.info("Successfully refreshed Circle.so token")
        return RefreshTokenResponse(**response)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error during Circle.so token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh Circle.so token",
        )
