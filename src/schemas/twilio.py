from pydantic import BaseModel, Field


class TwilioWebhookRequest(BaseModel):
    """
    Pydantic schema for validating the incoming webhook request from Twilio.

    Twilio sends webhook data as a form post (application/x-www-form-urlencoded).
    FastAPI will automatically handle parsing this into the model.
    """

    message_sid: str = Field(..., alias="MessageSid")
    account_sid: str = Field(..., alias="AccountSid")
    messaging_service_sid: str | None = Field(None, alias="MessagingServiceSid")
    from_: str = Field(..., alias="From")
    to: str = Field(..., alias="To")
    body: str = Field(..., alias="Body")
    num_media: int = Field(..., alias="NumMedia")

    model_config = {
        # Pydantic V2 configuration.
        # `populate_by_name` allows populating a model field by either its name or its alias.
        "populate_by_name": True
    }
