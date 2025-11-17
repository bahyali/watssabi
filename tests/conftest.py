import base64
import hashlib
import hmac
import os
from typing import AsyncGenerator, Callable, Dict

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.db.models import Base


def pytest_configure():
    """
    Set environment variables required for the application settings to load
    before any tests are collected.
    """
    # For local testing, services are accessed via localhost as ports are exposed.
    # The test runner runs on the host, so it connects to services via localhost.
    os.environ["POSTGRES_SERVER"] = "localhost"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "test_db"
    os.environ["POSTGRES_USER"] = "test_user"
    os.environ["POSTGRES_PASSWORD"] = "test_password"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["TWILIO_AUTH_TOKEN"] = "test_auth_token_from_env"
    os.environ["TWILIO_ACCOUNT_SID"] = "test_account_sid_from_env"
    os.environ["TWILIO_PHONE_NUMBER"] = "whatsapp:+1234567890"
    os.environ["OPENAI_API_KEY"] = "test_api_key"


@pytest_asyncio.fixture(scope="function")
async def test_db_session(monkeypatch) -> AsyncGenerator[AsyncSession, None]:
    """
    Fixture to create an isolated test database session for each test function.
    - Creates a new test database engine based on test environment variables.
    - Monkeypatches the application's session maker to use this test engine.
    - Creates all database tables before the test runs.
    - Yields a session for the test to use for assertions.
    - Drops all database tables after the test completes.
    """
    from src.core.config import settings

    async_engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    TestAsyncSessionLocal = async_sessionmaker(
        bind=async_engine, autocommit=False, autoflush=False, expire_on_commit=False
    )

    # Monkeypatch the session maker used by the ConversationService and any other
    # part of the application that might need it.
    monkeypatch.setattr(
        "src.services.conversation_service.AsyncSessionLocal", TestAsyncSessionLocal
    )

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await async_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_redis_client(monkeypatch) -> AsyncGenerator[aioredis.Redis, None]:
    """
    Fixture to create an isolated test Redis client for each test function.
    - Creates a new client pointing to a test Redis database (DB 1).
    - Monkeypatches the application's shared Redis client.
    - Yields the client for the test to use.
    - Flushes the test Redis database after the test completes.
    """
    from src.core.config import settings

    # Use a different database number for tests to avoid conflicts with dev
    test_redis = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=1,
        decode_responses=True,
    )

    # Monkeypatch the redis client used by the SessionManager
    monkeypatch.setattr("src.services.session_manager._redis_client", test_redis)

    yield test_redis

    await test_redis.flushdb()
    await test_redis.aclose()


@pytest.fixture(scope="session")
def twilio_signature_generator() -> Callable[[str, Dict, str], str]:
    """
    Returns a reusable helper function to generate a valid Twilio signature.
    This allows tests to create valid signatures for mocked webhook requests.
    """

    def _generate_signature(url: str, params: dict, auth_token: str) -> str:
        message = url
        if params:
            sorted_params = sorted(params.items())
            for key, value in sorted_params:
                message += key + value

        auth_token_bytes = auth_token.encode("utf-8")
        message_bytes = message.encode("utf-8")

        digest = hmac.new(auth_token_bytes, message_bytes, hashlib.sha1).digest()
        return base64.b64encode(digest).decode("utf-8")

    return _generate_signature
