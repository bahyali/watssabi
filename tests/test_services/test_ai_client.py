from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import APIError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice, CompletionUsage

from src.services.ai_client import AIClient


@pytest.fixture
def mock_openai_client():
    """Fixture to mock the AsyncOpenAI client."""
    with patch("src.services.ai_client.AsyncOpenAI") as mock_client_constructor:
        mock_instance = AsyncMock()
        mock_client_constructor.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_get_ai_response_success(mock_openai_client):
    """
    Tests that get_ai_response successfully calls the OpenAI API and returns a parsed response.
    """
    # Arrange
    ai_client = AIClient()
    system_prompt = "You are a helpful assistant."
    conversation_history = [{"role": "user", "content": "Hello"}]
    expected_response_content = "Hi there! How can I help?"

    # Mock the API response with explicit keyword arguments for robustness
    mock_message = ChatCompletionMessage(
        content=expected_response_content,
        role="assistant",
        function_call=None,
        tool_calls=None,
    )
    mock_choice = Choice(
        finish_reason="stop",
        index=0,
        message=mock_message,
        logprobs=None,
    )
    mock_completion = ChatCompletion(
        id="chatcmpl-123",
        choices=[mock_choice],
        created=1677652288,
        model="gpt-3.5-turbo-0613",
        object="chat.completion",
        usage=CompletionUsage(completion_tokens=9, prompt_tokens=10, total_tokens=19),
    )
    mock_openai_client.chat.completions.create.return_value = mock_completion

    # Act
    response = await ai_client.get_ai_response(system_prompt, conversation_history)

    # Assert
    assert response == expected_response_content
    mock_openai_client.chat.completions.create.assert_awaited_once()
    call_args = mock_openai_client.chat.completions.create.call_args
    assert call_args.kwargs["model"] == "gpt-3.5-turbo"
    expected_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Hello"},
    ]
    assert call_args.kwargs["messages"] == expected_messages


@pytest.mark.asyncio
async def test_get_ai_response_api_error(mock_openai_client):
    """
    Tests that get_ai_response returns None when an OpenAI APIError occurs.
    """
    # Arrange
    ai_client = AIClient()
    system_prompt = "You are a helpful assistant."
    conversation_history = [{"role": "user", "content": "Hello"}]

    # Mock the API to raise an error. For openai>1.0, APIError requires a `request`.
    mock_openai_client.chat.completions.create.side_effect = APIError(
        "API Error", request=MagicMock(), body=None
    )

    # Act
    response = await ai_client.get_ai_response(system_prompt, conversation_history)

    # Assert
    assert response is None


def test_ai_client_initialization_no_key(monkeypatch):
    """
    Tests that AIClient raises a ValueError if OPENAI_API_KEY is not set.
    """
    # Arrange
    # Patch the settings object directly on the module where it is used.
    # This is more robust than string-based patching in this case.
    from src.services import ai_client

    monkeypatch.setattr(ai_client.settings, "OPENAI_API_KEY", "")

    # Act & Assert
    with pytest.raises(ValueError, match="OPENAI_API_KEY is not set"):
        # AIClient is imported at the top of the file, but it will use the
        # patched settings from its module scope upon instantiation.
        AIClient()
