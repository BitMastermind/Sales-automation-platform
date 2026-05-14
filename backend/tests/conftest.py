import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DB_URL = "postgresql+asyncpg://sales:sales@localhost:5432/sales_test"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Drop and recreate all tables in sales_test before the test session."""
    async def _run():
        from core.database import Base
        import models  # noqa: F401 — registers all ORM models

        engine = create_async_engine(TEST_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """ASGI test client wired to the test DB. Truncates all tables before each test."""
    # Clean slate
    clean_engine = create_async_engine(TEST_DB_URL, echo=False)
    async with clean_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE campaigns, leads, emails, replies, oauth_tokens, crm_updates CASCADE"
            )
        )
    await clean_engine.dispose()

    from main import app
    from core.database import get_db

    test_engine = create_async_engine(TEST_DB_URL, echo=False)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await test_engine.dispose()
