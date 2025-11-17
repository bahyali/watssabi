import json
from unittest.mock import AsyncMock

import pytest

from src.crud.repository import DataRepository
from src.services.ai_client import AIClient
from src.services.conversation_service import SYSTEM_PROMPT, ConversationService
from src.services.session_manager import SessionManager

# Test constants
USER_ID = "test_user_123"
USER_MESSAGE = "Hello, I need some help."
AI_RESPONSE = "Of course, how can I assist you today?"


@pytest.fixture
def mock_ai_client(mocker) -> AsyncMock:
    """Creates a mock AIClient with autospec to enforce method signatures."""
    return mocker.create_autospec(AIClient, instance=True)


@pytest.fixture
def mock_session_manager(mocker) -> AsyncMock:
    """Creates a mock SessionManager with autospec."""
    return mocker.create_autospec(SessionManager, instance=True)


@pytest.fixture
def mock_data_repository(mocker) -> AsyncMock:
    """Creates a mock DataRepository with autospec."""
    return mocker.create_autospec(DataRepository, instance=True)


@pytest.fixture
def conversation_service(
    mock_ai_client: AsyncMock,
    mock_session_manager: AsyncMock,
    mock_data_repository: AsyncMock,
) -> ConversationService:
    """Initializes the ConversationService with mocked dependencies."""
    return ConversationService(
        ai_client=mock_ai_client,
        session_manager=mock_session_manager,
        data_repository=mock_data_repository,
    )


@pytest.mark.asyncio
async def test_process_message_for_new_conversation(
    conversation_service: ConversationService,
    mock_ai_client: AsyncMock,
    mock_session_manager: AsyncMock,
):
    """
    Tests the 'happy path' for a user starting a new conversation.
    - It should fetch the session (getting None).
    - It should call the AI with the new user message.
    - It should save the full history (user + AI) to the session.
    - It should return the AI's response.
    """
    # Arrange
    mock_session_manager.get_session.return_value = None
    mock_ai_client.get_ai_response.return_value = AI_RESPONSE

    # Act
    response = await conversation_service.process_message(USER_ID, USER_MESSAGE)

    # Assert
    mock_session_manager.get_session.assert_awaited_once_with(USER_ID)

    expected_history_for_ai = [{"role": "user", "content": USER_MESSAGE}]
    mock_ai_client.get_ai_response.assert_awaited_once_with(
        system_prompt=SYSTEM_PROMPT, conversation_history=expected_history_for_ai
    )

    expected_history_to_save = [
        {"role": "user", "content": USER_MESSAGE},
        {"role": "assistant", "content": AI_RESPONSE},
    ]
    mock_session_manager.set_session.assert_awaited_once_with(
        USER_ID, expected_history_to_save
    )

    assert response == AI_RESPONSE


@pytest.mark.asyncio
async def test_process_message_for_ongoing_conversation(
    conversation_service: ConversationService,
    mock_ai_client: AsyncMock,
    mock_session_manager: AsyncMock,
):
    """
    Tests the 'happy path' for a user with an existing conversation.
    - It should fetch the existing session history.
    - It should call the AI with the combined history.
    - It should save the fully updated history.
    - It should return the AI's response.
    """
    # Arrange
    previous_history = [{"role": "user", "content": "Previous message"}]
    mock_session_manager.get_session.return_value = previous_history.copy()
    mock_ai_client.get_ai_response.return_value = AI_RESPONSE

    # Act
    response = await conversation_service.process_message(USER_ID, USER_MESSAGE)

    # Assert
    mock_session_manager.get_session.assert_awaited_once_with(USER_ID)

    expected_history_for_ai = [
        {"role": "user", "content": "Previous message"},
        {"role": "user", "content": USER_MESSAGE},
    ]
    mock_ai_client.get_ai_response.assert_awaited_once_with(
        system_prompt=SYSTEM_PROMPT, conversation_history=expected_history_for_ai
    )

    expected_history_to_save = [
        {"role": "user", "content": "Previous message"},
        {"role": "user", "content": USER_MESSAGE},
        {"role": "assistant", "content": AI_RESPONSE},
    ]
    mock_session_manager.set_session.assert_awaited_once_with(
        USER_ID, expected_history_to_save
    )

    assert response == AI_RESPONSE


@pytest.mark.asyncio
async def test_process_message_returns_none_when_ai_fails(
    conversation_service: ConversationService,
    mock_ai_client: AsyncMock,
    mock_session_manager: AsyncMock,
):
    """
    Tests the scenario where the AI client fails to return a response.
    - It should fetch the session and call the AI.
    - It should NOT save anything to the session.
    - It should return None.
    """
    # Arrange
    mock_session_manager.get_session.return_value = []
    mock_ai_client.get_ai_response.return_value = None

    # Act
    response = await conversation_service.process_message(USER_ID, USER_MESSAGE)

    # Assert
    mock_session_manager.get_session.assert_awaited_once_with(USER_ID)

    expected_history_for_ai = [{"role": "user", "content": USER_MESSAGE}]
    mock_ai_client.get_ai_response.assert_awaited_once_with(
        system_prompt=SYSTEM_PROMPT, conversation_history=expected_history_for_ai
    )

    mock_session_manager.set_session.assert_not_awaited()

    assert response is None


@pytest.mark.asyncio
async def test_process_message_handles_completion(
    mocker,
    conversation_service: ConversationService,
    mock_ai_client: AsyncMock,
    mock_session_manager: AsyncMock,
    mock_data_repository: AsyncMock,
):
    """
    Tests the completion path where the AI returns a JSON object.
    - It should parse the JSON.
    - It should save the data via the repository.
    - It should delete the session.
    - It should return the final reply message.
    """
    # Arrange
    final_data_from_ai = {
        "reply": "Thanks! We've got your info.",
        "data": {"name": "John Doe", "email": "john.doe@example.com"},
    }
    ai_json_response = json.dumps(final_data_from_ai)
    mock_ai_client.get_ai_response.return_value = ai_json_response
    mock_session_manager.get_session.return_value = []

    # Mock the database interaction within _handle_conversation_completion
    mock_user = mocker.MagicMock()
    mock_user.user_id = "mock_user_uuid"

    # Mock the result of db.execute to simulate finding a user
    mock_execute_result = mocker.MagicMock()
    mock_execute_result.scalars.return_value.first.return_value = mock_user

    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = mock_execute_result
    mock_db_session.add = mocker.MagicMock()

    # Patch AsyncSessionLocal to return our mock session via the context manager
    mock_async_session_local = mocker.patch(
        "src.services.conversation_service.AsyncSessionLocal"
    )
    mock_async_session_local.return_value.__aenter__.return_value = mock_db_session

    # Act
    response = await conversation_service.process_message(USER_ID, "Here is my email.")

    # Assert
    mock_ai_client.get_ai_response.assert_awaited_once()

    # Verify data repository was called correctly.
    mock_data_repository.create_collected_data.assert_awaited_once()
    call_args = mock_data_repository.create_collected_data.call_args
    assert call_args.kwargs["db"] == mock_db_session
    assert call_args.kwargs["user_id"] == mock_user.user_id
    assert "conversation_id" in call_args.kwargs
    assert call_args.kwargs["data"] == final_data_from_ai["data"]

    # Verify session was deleted
    mock_session_manager.delete_session.assert_awaited_once_with(USER_ID)

    # Verify the correct reply was returned
    assert response == final_data_from_ai["reply"]

    # Verify session was not set (it was deleted instead)
    mock_session_manager.set_session.assert_not_awaited()
