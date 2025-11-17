import json
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CollectedData, Conversation, User
from src.main import app

# Constants for the test
TEST_USER_ID = "whatsapp:+15551234567"
BASE_URL = "http://testserver"
WEBHOOK_URL = "/webhook/twilio/"
TEST_AUTH_TOKEN = "test_auth_token_e2e"

# Define the full conversation scenario
USER_MESSAGES = [
    "Hi",
    "My name is Jane Doe",
    "My email is jane.doe@example.com",
    "Yes, that's correct",
]

# The final data structure the AI should return
FINAL_DATA_PAYLOAD = {
    "reply": "Thank you, Jane! Your information has been saved.",
    "data": {
        "full_name": "Jane Doe",
        "email_address": "jane.doe@example.com",
    },
}

# Mock AI responses corresponding to each user message
AI_RESPONSES = [
    "Hello! I'm here to collect some information. What is your full name?",
    "Got it. And what is your email address?",
    "Great. Just to confirm, your name is Jane Doe and your email is jane.doe@example.com. Is that correct?",
    json.dumps(FINAL_DATA_PAYLOAD),  # The final response is a JSON string
]


@pytest.mark.asyncio
async def test_full_conversation_and_data_persistence(
    mocker,
    monkeypatch,
    test_db_session: AsyncSession,
    test_redis_client,  # Fixture provides a clean, patched redis client
    twilio_signature_generator,
):
    """
    End-to-end test for a full, successful conversation.
    - Mocks the AIClient to return a predictable sequence of responses.
    - Simulates a user sending a series of messages via the Twilio webhook.
    - Verifies that the final collected data is correctly persisted to the database.
    - Verifies that the user's session is cleared from Redis upon completion.
    """
    # 1. Setup Mocks
    monkeypatch.setattr("src.core.config.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)
    monkeypatch.setattr("src.core.config.settings.OPENAI_API_KEY", "test_api_key")

    # Mock the AIClient where it's used in the webhook endpoint
    mock_ai_client_class = mocker.patch("src.api.endpoints.twilio_webhook.AIClient")
    mock_ai_instance = AsyncMock()
    # Set the side_effect to return responses from our list one by one
    mock_ai_instance.get_ai_response.side_effect = AI_RESPONSES
    mock_ai_client_class.return_value = mock_ai_instance

    # 2. Simulate the conversation via HTTP requests
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        for i, message in enumerate(USER_MESSAGES):
            payload = {
                "From": TEST_USER_ID,
                "Body": message,
                "To": "whatsapp:+1234567890",
                "MessageSid": f"SM{i:032x}",  # Unique SID for each message
                "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "NumMedia": "0",
            }
            full_url = f"{BASE_URL}{WEBHOOK_URL}"
            signature = twilio_signature_generator(full_url, payload, TEST_AUTH_TOKEN)
            headers = {"X-Twilio-Signature": signature}

            response = await client.post(WEBHOOK_URL, data=payload, headers=headers)
            assert response.status_code == 200

    # 3. Verify the final state in the Database
    # Use the provided test_db_session to query the test database
    db = test_db_session

    # Verify User was created
    user_stmt = select(User).where(User.whatsapp_id == TEST_USER_ID)
    user_result = await db.execute(user_stmt)
    user = user_result.scalars().one_or_none()
    assert user is not None, "User was not created in the database"
    assert user.whatsapp_id == TEST_USER_ID

    # Verify Conversation was created and marked as completed
    convo_stmt = select(Conversation).where(Conversation.user_id == user.user_id)
    convo_result = await db.execute(convo_stmt)
    conversation = convo_result.scalars().one_or_none()
    assert conversation is not None, "Conversation was not created"
    assert conversation.status == "completed"

    # Verify CollectedData was saved correctly
    data_stmt = select(CollectedData).where(
        CollectedData.conversation_id == conversation.conversation_id
    )
    data_result = await db.execute(data_stmt)
    collected_data = data_result.scalars().one_or_none()
    assert collected_data is not None, "CollectedData was not saved"
    assert collected_data.data == FINAL_DATA_PAYLOAD["data"]

    # 4. Verify the final state in Redis (session cleanup)
    session_key = f"session:{TEST_USER_ID}"
    session_exists = await test_redis_client.exists(session_key)
    assert session_exists == 0, "Session data was not cleared from Redis"
