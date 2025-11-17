from fastapi import HTTPException, Request, status
from starlette.datastructures import URL
from twilio.request_validator import RequestValidator

from src.core.config import settings


def _canonical_request_url(request: Request) -> str:
    """
    Reconstructs the original request URL Twilio used, accounting for proxy headers.
    """
    url = URL(str(request.url))

    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    forwarded_host = request.headers.get("X-Forwarded-Host")
    original_host = request.headers.get("X-Original-Host")
    forwarded_port = request.headers.get("X-Forwarded-Port")

    netloc = forwarded_host or original_host

    if netloc and forwarded_port and ":" not in netloc:
        netloc = f"{netloc}:{forwarded_port}"

    if forwarded_proto or netloc:
        url = url.replace(
            scheme=forwarded_proto or url.scheme,
            netloc=netloc or url.netloc,
        )

    return str(url)


async def validate_twilio_request(request: Request):
    """
    Validates that a request is genuinely from Twilio and returns the form data.

    This is accomplished by verifying the 'X-Twilio-Signature' header.
    See: https://www.twilio.com/docs/usage/security#validating-requests

    Args:
        request: The incoming FastAPI request object.

    Raises:
        HTTPException: If the signature is missing or invalid.

    Returns:
        The form data from the request if validation is successful.
    """
    twilio_signature = request.headers.get("X-Twilio-Signature")
    if not twilio_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Twilio-Signature header.",
        )

    form_data = await request.form()
    try:
        items = form_data.multi_items()
    except AttributeError:
        items = form_data.items()

    form_dict = {key: value for key, value in items}

    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    url_to_validate = _canonical_request_url(request)
    is_valid = validator.validate(url_to_validate, form_dict, twilio_signature)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Twilio signature.",
        )

    return form_dict
