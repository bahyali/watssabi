import json
from unittest.mock import AsyncMock

import pytest

from src.services.session_manager import session_manager


@pytest.fixture
def mock_redis_client(mocker):
    """
    Fixture to mock the Redis client used by the SessionManager.
    It patches the `redis_client` attribute of the singleton `session_manager` instance.
    """
    # We patch the 'redis_client' attribute of the already-instantiated
    # session_manager object. This ensures our tests use the mock instead of
    # a real Redis client connection, avoiding the issue of the real client
    # being captured at import time.
    mock = mocker.patch.object(session_manager, "redis_client", new_callable=AsyncMock)
    return mock


@pytest.mark.asyncio
async def test_get_session_found(mock_redis_client):
    """
    Test get_session when a session exists in Redis.
    It should return the deserialized conversation history.
    """
    user_id = "test_user_123"
    expected_key = f"session:{user_id}"
    history = [{"role": "user", "content": "Hello"}]
    serialized_history = json.dumps(history)

    # Configure the mock's get method to return the serialized data
    mock_redis_client.get.return_value = serialized_history

    # Call the method under test
    result = await session_manager.get_session(user_id)

    # Assert that the mock was called correctly
    mock_redis_client.get.assert_awaited_once_with(expected_key)
    # Assert that the result is the correctly deserialized data
    assert result == history


@pytest.mark.asyncio
async def test_get_session_not_found(mock_redis_client):
    """
    Test get_session when no session exists in Redis.
    It should return None.
    """
    user_id = "test_user_456"
    expected_key = f"session:{user_id}"

    # Configure the mock's get method to return None, simulating a cache miss
    mock_redis_client.get.return_value = None

    # Call the method under test
    result = await session_manager.get_session(user_id)

    # Assert that the mock was called correctly
    mock_redis_client.get.assert_awaited_once_with(expected_key)
    # Assert that the result is None
    assert result is None


@pytest.mark.asyncio
async def test_set_session(mock_redis_client):
    """
    Test set_session to ensure it serializes data and calls Redis set with the correct parameters.
    """
    user_id = "test_user_789"
    history = [{"role": "assistant", "content": "Hi there!"}]
    expected_key = f"session:{user_id}"
    serialized_history = json.dumps(history)

    # Call the method under test
    await session_manager.set_session(user_id, history)

    # Assert that the mock's set method was called with the correct key,
    # serialized data, and expiration time (ttl).
    mock_redis_client.set.assert_awaited_once_with(
        expected_key, serialized_history, ex=session_manager.session_ttl
    )


@pytest.mark.asyncio
async def test_delete_session(mock_redis_client):
    """
    Test delete_session to ensure it calls Redis delete with the correct key.
    """
    user_id = "test_user_abc"
    expected_key = f"session:{user_id}"

    # Call the method under test
    await session_manager.delete_session(user_id)

    # Assert that the mock's delete method was called with the correct key
    mock_redis_client.delete.assert_awaited_once_with(expected_key)
