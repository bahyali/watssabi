import json
from typing import Any, Dict, List, Optional

import structlog
from sqlalchemy import select

from src.crud.repository import DataRepository
from src.db.base import AsyncSessionLocal
from src.db.models import Conversation, User
from src.services.ai_client import AIClient
from src.services.session_manager import SessionManager

log = structlog.get_logger()

SYSTEM_PROMPT = (
    "You are Watssabii, a friendly virtual host for an e-commerce concierge that helps "
    "shoppers pick the right products and share lightweight survey feedback. Keep the tone "
    "warm, respectful, and never intrusive. Open with a quick greeting that explains the flow: "
    "you will collect their contact information (full name + best email or SMS) and then walk "
    "through a few questions about what they're shopping for. Mention once at the start that "
    "they can skip anything or say \"done\" at any time, but do not repeat that reminder in every "
    "message.\n\n"
    "Conversation style:\n"
    "- For each turn, respond with a short, encouraging message that feels like a human chat.\n"
    "- Ask exactly one question at a time and wait for the answer before moving on.\n"
    "- Offer curated option lists when helpful (categories, price ranges, blockers), but always welcome free-form answers.\n"
    "- Clarify gently if the answer is ambiguous and summarize key preferences before switching topics.\n"
    "- Keep the flow efficient: once you have a confident answer, advance to the next item.\n\n"
    "Information to collect (in this order unless the user requests otherwise):\n"
    "Contact details:\n"
    "   1. Full name\n"
    "   2. Preferred follow-up channel (email, SMS, WhatsApp, etc.)\n"
    "Shopping context:\n"
    "1. The product category or type they are most interested in (e.g., apparel, electronics, home goods, skincare).\n"
    "2. Budget range or price comfort zone (offer bands like <$50, $50-150, $150-500, $500+ but accept any answer).\n"
    "3. Key purchase criteria or blockers (fit, sustainability, shipping speed, reviews, sizing, inventory, etc.). "
    "Encourage them to pick up to three priorities.\n"
    "4. Previous solutions they have tried—other stores, influencers, friends, comparison tools—and what worked or failed.\n"
    "5. Typical timeframe for making the purchase (immediate, this week, this month, just researching).\n\n"
    "After collecting all answers (or if the user says \"done\"), thank them warmly, "
    "include the sentence \"Thank you for helping us build a better solution.\", and "
    "let them know the concierge will follow up with curated recommendations.\n\n"
    "Once everything is gathered, reply with a JSON object with this exact shape:\n"
    '{\n'
    '  \"reply\": \"<warm final message including the outro>\",\n'
    '  \"data\": {\n'
    '    \"full_name\": \"<collected full name>\",\n'
    '    \"contact\": \"<email or preferred channel>\",\n'
    '    \"status\": \"<shopping category or intent>\",\n'
    '    \"blockers\": [\"<priority 1>\", \"<priority 2>\", ...],\n'
    '    \"help_sources\": [\"<previous sources>\", ...],\n'
    '    \"lawyer_cost\": \"<use None or repurpose as special_cost if relevant>\",\n'
    '    \"time_spent\": \"<purchase timeframe or research depth>\"\n'
    '  }\n'
    '}\n'
    "Until the conversation is complete, never respond with JSON—use natural, friendly text."
)


class ConversationService:
    """
    Orchestrates the conversation flow, including session management,
    AI interaction, and data persistence.
    """

    def __init__(
        self,
        ai_client: AIClient,
        session_manager: SessionManager,
        data_repository: DataRepository,
    ):
        """
        Initializes the ConversationService with its dependencies.

        Args:
            ai_client: The client for interacting with the AI model.
            session_manager: The manager for handling user session data.
            data_repository: The repository for database operations.
        """
        self.ai_client = ai_client
        self.session_manager = session_manager
        self.data_repository = data_repository

    async def _handle_conversation_completion(
        self, user_id: str, history: List[Dict[str, Any]], final_data: Dict[str, Any]
    ) -> str:
        """
        Handles the final persistence of conversation data to the database
        once the AI signals completion.

        Args:
            user_id: The user's WhatsApp ID.
            history: The full conversation history.
            final_data: The parsed JSON object from the AI.

        Returns:
            The final reply message to be sent to the user.
        """
        # The final AI response (the JSON object) should be part of the history.
        history.append({"role": "assistant", "content": json.dumps(final_data)})
        log.info("persisting_completed_conversation", user_id=user_id)

        async with AsyncSessionLocal() as db:
            # Step 1: Get or create the user and conversation in one transaction.
            stmt = select(User).where(User.whatsapp_id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()

            if not user:
                user = User(whatsapp_id=user_id)
                db.add(user)

            conversation = Conversation(
                user=user,
                status="completed",
                conversation_history=history,
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(user)
            await db.refresh(conversation)

        # Step 2: Create the collected data record in a separate transaction
        # to respect the DataRepository's interface which handles its own commits.
        async with AsyncSessionLocal() as db:
            data_to_save = final_data.get("data", {})
            if data_to_save:
                await self.data_repository.create_collected_data(
                    db=db,
                    user_id=user.user_id,
                    conversation_id=conversation.conversation_id,
                    data=data_to_save,
                )
        log.info(
            "persistence_successful",
            user_id=user.user_id,
            conversation_id=conversation.conversation_id,
        )
        reply_message = final_data.get("reply")
        if not isinstance(reply_message, str) or not reply_message.strip():
            reply_message = "Thank you! Your information has been saved."
        return reply_message

    async def process_message(self, user_id: str, message: str) -> Optional[str]:
        """
        Processes an incoming message from a user.

        If the AI's response is a JSON object, it triggers the data
        persistence flow. Otherwise, it continues the conversation.
        """
        bound_log = log.bind(user_id=user_id)
        bound_log.info("processing_user_message")
        # Retrieve the conversation history.
        history = await self.session_manager.get_session(user_id)
        if history is None:
            history = []

        # Append the new user message.
        history.append({"role": "user", "content": message})

        # Get a response from the AI.
        ai_response = await self.ai_client.get_ai_response(
            system_prompt=SYSTEM_PROMPT, conversation_history=history.copy()
        )

        # If the AI fails to respond, we stop here.
        if not ai_response:
            bound_log.error("no_response_from_ai")
            return None

        try:
            # Completion path: AI returns a JSON object.
            final_data = json.loads(ai_response)
            bound_log.info("conversation_completed")
            final_reply = await self._handle_conversation_completion(
                user_id, history, final_data
            )
            # Clean up the session after successful persistence.
            await self.session_manager.delete_session(user_id)
            bound_log.info("session_deleted")
            return final_reply
        except json.JSONDecodeError:
            # Ongoing conversation path: AI returns a plain string.
            bound_log.info("conversation_ongoing")
            history.append({"role": "assistant", "content": ai_response})
            await self.session_manager.set_session(user_id, history)
            return ai_response
