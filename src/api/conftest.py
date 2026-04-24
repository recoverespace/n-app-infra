import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from api.main import app
from data.lib.db import engine


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with session() as s:  # type: ignore
        async with engine.begin() as conn:
            # Drop and recreate schema with CASCADE to handle foreign key constraints
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
            await conn.commit()

        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            await conn.commit()
        yield s

    await engine.dispose()


@pytest.fixture(scope="function")
async def client(session) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),  # type: ignore
        base_url="http://test/",
    ) as c:
        yield c
