from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.datastructures import FormData, URL
from twilio.request_validator import RequestValidator

from src.core.security import validate_twilio_request

# A known test auth token
TEST_AUTH_TOKEN = "test_auth_token_12345"


def generate_twilio_signature(url: str, params: dict, auth_token: str) -> str:
    """
    Helper function to generate a valid Twilio signature for testing using Twilio's validator.
    """
    validator = RequestValidator(auth_token)
    return validator.compute_signature(url, params)


@pytest.mark.asyncio
async def test_validate_twilio_request_with_valid_signature(mocker):
    """
    Tests that a request with a valid signature passes validation and returns form data.
    """
    mocker.patch("src.core.security.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)

    test_url = "https://testserver.com/webhook/twilio"
    test_params = {"From": "+1234567890", "Body": "Hello"}

    expected_signature = generate_twilio_signature(
        test_url, test_params, TEST_AUTH_TOKEN
    )

    mock_request = AsyncMock()
    mock_request.url = URL(test_url)
    mock_request.headers = {"X-Twilio-Signature": expected_signature}
    mock_request.form.return_value = FormData(test_params.items())

    # This should not raise an exception and should return the form data
    form_data = await validate_twilio_request(mock_request)
    assert form_data == test_params


@pytest.mark.asyncio
async def test_validate_twilio_request_with_invalid_signature(mocker):
    """
    Tests that a request with an invalid signature raises a 403 Forbidden error.
    """
    mocker.patch("src.core.security.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)

    test_url = "https://testserver.com/webhook/twilio"
    test_params = {"From": "+1234567890", "Body": "Hello"}

    mock_request = AsyncMock()
    mock_request.url = URL(test_url)
    mock_request.headers = {"X-Twilio-Signature": "invalid_signature"}
    mock_request.form.return_value = FormData(test_params.items())

    with pytest.raises(HTTPException) as exc_info:
        await validate_twilio_request(mock_request)

    assert exc_info.value.status_code == 403
    assert "Invalid Twilio signature" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_twilio_request_with_missing_signature():
    """
    Tests that a request with a missing signature raises a 400 Bad Request error.
    """
    mock_request = AsyncMock()
    mock_request.url = URL("https://testserver.com/webhook/twilio")
    mock_request.headers = {}  # No signature header
    mock_request.form.return_value = FormData()

    with pytest.raises(HTTPException) as exc_info:
        await validate_twilio_request(mock_request)

    assert exc_info.value.status_code == 400
    assert "Missing X-Twilio-Signature header" in exc_info.value.detail


@pytest.mark.asyncio
async def test_validate_twilio_request_with_forwarded_headers(mocker):
    """
    Requests arriving through a proxy (e.g., ngrok) should validate using forwarded proto/host.
    """
    mocker.patch("src.core.security.settings.TWILIO_AUTH_TOKEN", TEST_AUTH_TOKEN)

    public_url = "https://example.ngrok-free.app/webhook/twilio"
    internal_url = "http://app:8000/webhook/twilio"
    test_params = {"From": "+1234567890", "Body": "Hi"}

    expected_signature = generate_twilio_signature(public_url, test_params, TEST_AUTH_TOKEN)

    mock_request = AsyncMock()
    mock_request.url = URL(internal_url)
    mock_request.headers = {
        "X-Twilio-Signature": expected_signature,
        "X-Forwarded-Proto": "https",
        "X-Forwarded-Host": "example.ngrok-free.app",
    }
    mock_request.form.return_value = FormData(test_params.items())

    form_data = await validate_twilio_request(mock_request)
    assert form_data == test_params
