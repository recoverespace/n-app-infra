import stripe

from api.settings import settings

stripe.api_key = settings.STRIPE_API_KEY


def create_customer(email: str, name: str) -> stripe.Customer:
    return stripe.Customer.create(email=email, name=name)


def create_payment_intent(
    amount: int, currency: str, stripe_id: str
) -> stripe.PaymentIntent:
    return stripe.PaymentIntent.create(
        amount=amount,
        currency=currency,
        customer=stripe_id,
        automatic_payment_methods={"enabled": True}
    )


def create_customer_ephemeral_key(customer_id: str, api_version: str) -> stripe.EphemeralKey:
    return stripe.EphemeralKey.create(customer=customer_id, api_version=api_version)
