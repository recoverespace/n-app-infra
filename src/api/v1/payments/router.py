import json
from typing import Any
from fastapi import APIRouter, status, HTTPException, Request
from api.lib.deps import DBDep, UserIDDep
from sqlmodel import and_, col
from common.otel import get_logger
from pydantic import BaseModel
from api.lib.stripe import stripe, create_customer, create_payment_intent, create_customer_ephemeral_key
from data.domain.users.crud import user_crud
from data.domain.users.models import User
from data.domain.users.schemas import UserRead, UserPaymentStatus as BaseUserPaymentStatus
from api.settings import settings

router = APIRouter(prefix="/payments")
logger = get_logger(__name__)


class UserPaymentStatus(BaseModel):
    user_id: int
    stripe_id: str | None
    has_paid: bool = False


class PaymentIntentRequest(BaseModel):
    amount: int
    currency: str
    api_version: str = "2020-03-02"


class EphemeralKey(BaseModel):
    created: int
    expires: int
    id: str
    secret: str


class PaymentIntentResponse(BaseModel):
    payment_intent_id: str
    amount: int
    currency: str
    client_secret: str
    confirmation_method: str
    created: int
    customer: str
    status: str
    ephemeral_key: EphemeralKey
    publishable_key: str = stripe.api_key


class WebhookResponse(BaseModel):
    success: bool


@router.get("/status/me", summary="Get current user payment status")
async def get_me_payment_status(user_id=UserIDDep, db=DBDep) -> UserRead:
    user = await user_crud.get(
        and_(col(User.id) == user_id, col(User.is_active) == True, col(User.is_deleted) == False), db=db
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserPaymentStatus(
        user_id=user.id, stripe_id=user.stripe_id, has_paid=user.payment_status == BaseUserPaymentStatus.paid
    )


@router.get("/status", summary="Get user payment status")
async def get_user_payment_status(user_id=int, db=DBDep) -> UserRead:
    user = await user_crud.get(
        and_(col(User.id) == user_id, col(User.is_active) == True, col(User.is_deleted) == False), db=db
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserPaymentStatus(
        user_id=user.id, stripe_id=user.stripe_id, has_paid=user.payment_status == BaseUserPaymentStatus.paid
    )


@router.post("/createIntent", summary="Create payment intent")
async def post_payment_intent(intent_in: PaymentIntentRequest, user_id=UserIDDep, db=DBDep) -> UserRead:
    user = await user_crud.get(
        and_(col(User.id) == user_id, col(User.is_active) == True, col(User.is_deleted) == False), db=db
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.stripe_id:
        logger.info(f"User {user_id} does not have a stripe_id")
        stipe_id = create_customer(user.email, user.display_name)
        await user_crud.update(user, {"stripe_id": stipe_id}, db=db)
    payment_intent = create_payment_intent(intent_in.amount, intent_in.currency, user.stripe_id)
    logger.info(f"Created payment intent {payment_intent.id} for user {user_id}")
    ephemeral_key = create_customer_ephemeral_key(user.stripe_id, intent_in.api_version).secret
    logger.info(f"Created ephemeral key for user {user_id}")
    return PaymentIntentResponse(
        payment_intent_id=payment_intent.id,
        amount=payment_intent.amount,
        currency=payment_intent.currency,
        client_secret=payment_intent.client_secret,
        confirmation_method=payment_intent.confirmation_method,
        created=payment_intent.created,
        customer=payment_intent.customer,
        status=payment_intent.status,
        ephemeral_key=EphemeralKey(
            created=ephemeral_key.created,
            expires=ephemeral_key.expires,
            id=ephemeral_key.id,
            secret=ephemeral_key.secret,
        ),
    )


@router.post("/webhook", summary="Stripe webhook")
async def stripe_webhook(request: Request, db=DBDep) -> WebhookResponse:
    event = None
    payload = request.data
    try:
        event = json.loads(payload)
    except json.decoder.JSONDecodeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from e
    if settings.STRIPE_WEBHOOK_SECRET:
        sig_header = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from e

    if event and event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        logger.info("Payment for {} succeeded".format(payment_intent["amount"]))
        stripe_id = payment_intent["customer"]
        user = await user_crud.get(User.stripe_id == stripe_id, db=db)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        await user_crud.update(user, {"payment_status": BaseUserPaymentStatus.paid}, db=db)
    else:
        logger("Unhandled event type {}".format(event["type"]))

    return WebhookResponse(success=True)
