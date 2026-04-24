from api.lib.tests.fake.types import fake_first_name, fake_last_name, fake_url, fake_uuid


def firebase_user_factory(**kwargs) -> dict[str, str]:
    first_name = kwargs.get("first_name", fake_first_name())
    last_name = kwargs.get("first_name", fake_last_name())
    return {
        "external_id": kwargs.get("external_id", fake_uuid()),
        "first_name": first_name,
        "last_name": last_name,
        "avatar_url": kwargs.get("avatar_url", fake_url()),
        "display_name": f"{first_name} {last_name}",
        "email": kwargs.get("email", f"{fake_uuid()}@example.com"),
    }
