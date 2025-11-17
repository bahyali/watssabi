import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import ValidationError
from twilio.twiml.messaging_response import MessagingResponse

from src.core.security import validate_twilio_request
from src.crud.repository import data_repository
from src.schemas.twilio import TwilioWebhookRequest
from src.services.ai_client import AIClient
from src.services.conversation_service import ConversationService
from src.services.session_manager import session_manager

router = APIRouter()
log = structlog.get_logger()


@router.post(
    "/",
    summary="Handle Incoming Twilio Messages",
    # Twilio expects a 200 OK with TwiML, not 204
    status_code=status.HTTP_200_OK,
)
async def handle_twilio_webhook(
    # This dependency validates the request signature and returns the form data
    form_data: dict = Depends(validate_twilio_request),
):
    """
    Receives, validates, and processes incoming messages from Twilio.
    - Validates Twilio signature.
    - Parses the incoming request body.
    - Passes the message to the ConversationService to get a reply.
    - Constructs a TwiML response to send the reply back to the user.
    """
    log.info("twilio_webhook_received")
    try:
        # Parse and validate the form data into a Pydantic model
        webhook_data = TwilioWebhookRequest.model_validate(form_data)
        log.bind(
            from_number=webhook_data.from_, message_sid=webhook_data.message_sid
        ).info("webhook_payload_validated")

    except ValidationError as exc:
        log.error("webhook_validation_error", detail=exc.errors(), form_data=form_data)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc

    # In a production app with dependency injection, this would be handled differently.
    # For now, direct instantiation is sufficient for the task.
    ai_client = AIClient()
    conversation_service = ConversationService(
        ai_client=ai_client,
        session_manager=session_manager,
        data_repository=data_repository,
    )

    # Process the message using the conversation service to get a reply
    ai_reply = await conversation_service.process_message(
        user_id=webhook_data.from_, message=webhook_data.body
    )

    # Create a TwiML response object to build the reply
    response = MessagingResponse()

    # Add the AI's message to the response.
    # If the AI fails, provide a fallback message.
    if ai_reply:
        response.message(ai_reply)
        log.info("sending_ai_reply")
    else:
        response.message("Sorry, I encountered a problem. Please try again later.")
        log.warning("sending_fallback_reply")

    # Return the TwiML response as XML
    return Response(content=str(response), media_type="application/xml")
