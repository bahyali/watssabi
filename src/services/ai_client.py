from typing import Dict, List

import structlog
from openai import APIError, AsyncOpenAI

from src.core.config import settings

log = structlog.get_logger()


class AIClient:
    """
    A client to encapsulate communication with an LLM provider (OpenAI).
    """

    def __init__(self):
        """
        Initializes the asynchronous OpenAI client.
        """
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables.")
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def get_ai_response(
        self,
        system_prompt: str,
        conversation_history: List[Dict[str, str]],
        model: str = "gpt-5-mini",
    ) -> str | None:
        """
        Gets a response from the AI based on the conversation history and a system prompt.

        Args:
            system_prompt: The initial prompt that sets the AI's role and instructions.
            conversation_history: A list of previous messages in the conversation.
            model: The name of the model to use for the completion.

        Returns:
            The AI's response as a string, or None if an error occurred.
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)

        try:
            log.info("sending_request_to_ai", model=model)
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,  # type: ignore
            )

            ai_response = response.choices[0].message.content
            log.info("received_response_from_ai")
            return ai_response.strip() if ai_response else None

        except APIError as e:
            log.error("openai_api_error", error=str(e))
            return None
        except (IndexError, AttributeError) as e:
            log.error("openai_response_parsing_error", error=str(e))
            return None
