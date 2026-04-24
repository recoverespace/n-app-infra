import random
from uuid import uuid4

from faker import Faker

_faker = Faker()


def fake_first_name() -> str:
    return _faker.first_name()


def fake_last_name() -> str:
    return _faker.last_name()


def fake_url() -> str:
    return _faker.url()


def fake_uuid() -> str:
    return str(uuid4())


def fake_datetime() -> str:
    return _faker.date_time().isoformat()


def fake_json() -> str:
    return _faker.json()


def fake_bool() -> bool:
    return random.random() > 0.5


def fake_version() -> str:
    return f'{_faker.random_int(0, 5)}.{_faker.random_int(0, 99)}.{
        _faker.random_int(0, 100)}'


def fake_model() -> str:
    return random.choice(
        [
            f'iPhone {_faker.random_int(9, 14)}',
            f'Samsung S{_faker.random_int(8, 24)}',
        ]
    )

def fake_platform() -> str:
    return random.choice(['ios', 'android'])


def fake_store() -> str:
    return random.choice(['app_store', 'play_store'])


def fake_timezone() -> str:
    return _faker.timezone()


def fake_language() -> str:
    return _faker.locale()