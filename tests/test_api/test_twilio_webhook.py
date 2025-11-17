import pytest
from httpx import ASGITransport, AsyncClient
from twilio.twiml.messaging_response import MessagingResponse

from src.main import app

# A known test auth token, must be consistent
TEST_AUTH_TOKEN = "test_auth_token_12345"
BASE_URL = "http://testserver"
WEBHOOK_URL = "/webhook/twilio/"

# A full, valid payload to be reused across tests
VALID_PAYLOAD = {
    "MessageSid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "AccountSid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    "From": "whatsapp:+14155238886",
    "To": "whatsapp:+14155238887",
    "Body": "Hello from test",
    "NumMedia": "0",
}


@pytest.mark.asyncio
async def test_webhook_with_valid_signature_succeeds(
    mocker, monkeypatch, twilio_signature_generator
):
    """
    Tests that a POST request with a valid signature to the webhook succeeds (200),
    calls the ConversationService, and returns a valid TwiML response.
    """
    # Patch settings used by the security validator
    monkeypatch.setattr("src.core.config.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)
    # Patch settings used by the AIClient to prevent real API calls
    monkeypatch.setattr("src.core.config.settings.OPENAI_API_KEY", "test_api_key")

    # Mock the ConversationService dependency in the webhook module
    mock_conversation_service = mocker.patch(
        "src.api.endpoints.twilio_webhook.ConversationService"
    )

    # Mock the instance and its async method
    mock_ai_reply = "Hello! This is the AI speaking."
    mock_instance = mocker.AsyncMock()
    mock_instance.process_message.return_value = mock_ai_reply
    mock_conversation_service.return_value = mock_instance

    payload = VALID_PAYLOAD
    user_id = payload["From"]
    user_message = payload["Body"]

    # The URL must match exactly what the server will see
    full_url = f"{BASE_URL}{WEBHOOK_URL}"

    signature = twilio_signature_generator(full_url, payload, TEST_AUTH_TOKEN)
    headers = {"X-Twilio-Signature": signature}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        response = await client.post(WEBHOOK_URL, data=payload, headers=headers)

    # 1. Assert the response is successful and has the correct content type
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"

    # 2. Verify the ConversationService was called correctly
    mock_instance.process_message.assert_awaited_once_with(
        user_id=user_id, message=user_message
    )

    # 3. Verify the TwiML response is correct
    expected_twiml = MessagingResponse()
    expected_twiml.message(mock_ai_reply)
    assert response.text == str(expected_twiml)


@pytest.mark.asyncio
async def test_webhook_with_ai_failure(mocker, monkeypatch, twilio_signature_generator):
    """
    Tests that the webhook returns a fallback message if the ConversationService
    returns None.
    """
    # Patch settings
    monkeypatch.setattr("src.core.config.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)
    monkeypatch.setattr("src.core.config.settings.OPENAI_API_KEY", "test_api_key")

    # Mock the ConversationService to simulate a failure (returns None)
    mock_conversation_service = mocker.patch(
        "src.api.endpoints.twilio_webhook.ConversationService"
    )
    mock_instance = mocker.AsyncMock()
    mock_instance.process_message.return_value = None  # Simulate failure
    mock_conversation_service.return_value = mock_instance

    payload = VALID_PAYLOAD
    full_url = f"{BASE_URL}{WEBHOOK_URL}"
    signature = twilio_signature_generator(full_url, payload, TEST_AUTH_TOKEN)
    headers = {"X-Twilio-Signature": signature}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        response = await client.post(WEBHOOK_URL, data=payload, headers=headers)

    assert response.status_code == 200

    # Verify the TwiML response contains the fallback message
    fallback_message = "Sorry, I encountered a problem. Please try again later."
    expected_twiml = MessagingResponse()
    expected_twiml.message(fallback_message)
    assert response.text == str(expected_twiml)


@pytest.mark.asyncio
async def test_webhook_with_invalid_signature_fails(monkeypatch):
    """
    Tests that a POST request with an invalid signature is rejected (403).
    """
    monkeypatch.setattr("src.core.config.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)

    payload = VALID_PAYLOAD
    headers = {"X-Twilio-Signature": "this_is_not_valid"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        response = await client.post(WEBHOOK_URL, data=payload, headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_with_missing_signature_fails():
    """
    Tests that a POST request with a missing signature is rejected (400).
    """
    payload = VALID_PAYLOAD
    headers = {}  # No signature header

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=BASE_URL
    ) as client:
        response = await client.post(WEBHOOK_URL, data=payload, headers=headers)

    assert response.status_code == 400
