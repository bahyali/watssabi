from fastapi import FastAPI

from src.api.endpoints import twilio_webhook
from src.core.config import settings
from src.core.logging import setup_logging

# Configure logging before creating the app instance
setup_logging()

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(
    twilio_webhook.router,
    prefix="/webhook/twilio",
    tags=["Webhooks"],
)


@app.get("/health")
def health_check():
    """
    Health check endpoint to verify that the service is running.
    """
    return {"status": "ok"}
