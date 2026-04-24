from typing import Optional, List, Dict, Any

import httpx
from fastapi import HTTPException, status
from api.settings import settings
from common.otel import get_logger
from urllib.parse import quote

logger = get_logger(__name__)


class CircleService:
    BASE_URL = "https://app.circle.so/api"

    def __init__(self):
        self.api_key = settings.CIRCLE_ADMIN_API_KEY
        self.headless_api_key = settings.CIRCLE_HEADLESS_API_KEY
        self.space_id = settings.CIRCLE_SPACE_ID
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.headless_headers = {
            "Authorization": f"Bearer {self.headless_api_key}",
            "Content-Type": "application/json",
        }

    async def get_token(self, email: str) -> Dict[str, Any]:
        """
        Get Circle.so token using headless API.
        Returns full response if successful, raises appropriate HTTPException otherwise.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/v1/headless/auth_token",
                    headers=self.headless_headers,
                    json={"email": email},
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Circle.so authentication failed",
                    )
                elif response.status_code == 422:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="User not found in Circle.so",
                    )
                elif response.status_code == 403:
                    logger.error("Circle.so headless API access not available")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Circle.so integration is not available",
                    )
                else:
                    logger.error(f"Unexpected response from Circle.so: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to get Circle.so token",
                    )

            except httpx.RequestError as e:
                logger.error(f"Request to Circle.so failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to communicate with Circle.so",
                )

    async def create_member(
        self,
        email: str,
        name: Optional[str] = None,
        password: Optional[str] = None,
        skip_invitation: bool = True,
        avatar: Optional[str] = None,
        headline: Optional[str] = None,
        is_flagged: bool = False,
        preferences: Optional[Dict[str, bool]] = None,
        space_ids: Optional[List[int]] = None,
        space_group_ids: Optional[List[int]] = None,
        member_tag_ids: Optional[List[int]] = None,
        community_member_profile_fields: Optional[Dict[str, str]] = None,
    ) -> dict:
        payload = {
            "email": email,
            "skip_invitation": skip_invitation,
            "is_flagged": is_flagged,
        }

        if name:
            payload["name"] = name
        if password:
            payload["password"] = password
        if avatar:
            payload["avatar_url"] = avatar
        if headline:
            payload["headline"] = headline
        if preferences:
            payload["preferences"] = preferences
        if space_ids:
            payload["space_ids"] = [int(space_id) for space_id in space_ids]
        if space_group_ids:
            payload["space_group_ids"] = space_group_ids
        if member_tag_ids:
            payload["member_tag_ids"] = member_tag_ids
        if community_member_profile_fields:
            payload["community_member_profile_fields"] = community_member_profile_fields

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/admin/v2/community_members",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                error_body = (
                    e.response.json() if e.response.content else "No error body"
                )
                logger.error(
                    f"Circle.so API error: status={e.response.status_code}, "
                    f"error_body={error_body}, "
                    f"request_payload={payload}, "
                    f"headers={self.headers}"
                )
                raise

    async def create_member_for_user(
        self,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> None:
        if not email:
            logger.warning("Skipping Circle.so user creation: email not available")
            return

        name = " ".join(filter(None, [first_name, last_name])) or display_name or email

        try:
            await self.create_member(
                email=email,
                name=name,
                space_ids=[self.space_id],
                skip_invitation=True,
            )
            logger.info(f"Successfully created Circle.so user for {email}")
        except Exception as e:
            logger.warning(
                f"Failed to create Circle.so user for {email}. " f"Error: {str(e)}"
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh Circle.so access token using a refresh token.
        Returns new access token and its expiration time if successful.
        Raises appropriate HTTPException otherwise.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.patch(
                    f"{self.BASE_URL}/v1/headless/access_token/refresh",
                    headers=self.headless_headers,
                    json={"refresh_token": refresh_token},
                )

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="The refresh token is expired. Please generate/get new auth token.",
                    )
                elif response.status_code == 403:
                    logger.error("Circle.so headless API access not available")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Circle.so integration is not available",
                    )
                elif response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Refresh token not found.",
                    )
                elif response.status_code == 422:
                    error_body = response.json()
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="The access token generation failed. Please contact support.",
                        headers={"error_details": error_body.get("error_details", {})},
                    )
                else:
                    logger.error(f"Unexpected response from Circle.so: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to refresh Circle.so token",
                    )

            except httpx.RequestError as e:
                logger.error(f"Request to Circle.so failed: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to communicate with Circle.so",
                )


circle_service = CircleService()
