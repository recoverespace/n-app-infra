import json

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from data.settings import settings

DB_POOL_SIZE = 83
WEB_CONCURRENCY = 9
POOL_SIZE = max(DB_POOL_SIZE // WEB_CONCURRENCY, 5)


def custom_serializer(d):
    return json.dumps(d, default=lambda v: v.json())


engine = create_async_engine(
    str(settings.POSTGRES_DSN),
    echo=False,
    pool_pre_ping=True,
    future=True,
)


SessionLocal = sessionmaker(  # type: ignore
    bind=engine,  # type: ignore
    autoflush=False,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
)
