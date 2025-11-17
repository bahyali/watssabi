import json
from typing import List, Optional

import redis.asyncio as aioredis
import structlog
from redis.exceptions import RedisError

from src.core.config import settings

log = structlog.get_logger()

# Module-level Redis client instance for connection pooling.
# This is created once when the module is imported, and shared across the application.
_redis_client = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,  # Decode responses from bytes to UTF-8 strings
)


class SessionManager:
    """
    Manages user conversation sessions in Redis.

    This class provides an asynchronous interface to get, set, and delete
    conversation history for a given user, using Redis as a stateless session store.
    It uses a singleton pattern by instantiating it once at the module level.
    """

    def __init__(self):
        self.redis_client = _redis_client
        self.session_ttl = 3600  # Session timeout in seconds (1 hour)

    def _get_session_key(self, user_id: str) -> str:
        """Generates a consistent Redis key for a user's session."""
        return f"session:{user_id}"

    async def get_session(self, user_id: str) -> Optional[List[dict]]:
        """
        Retrieves a user's conversation history from Redis.

        Args:
            user_id: The unique identifier for the user.

        Returns:
            A list of message dictionaries representing the conversation history,
            or None if no session is found.
        """
        key = self._get_session_key(user_id)
        try:
            session_data = await self.redis_client.get(key)
            if session_data:
                return json.loads(session_data)
        except RedisError as e:
            log.error("redis_get_session_error", user_id=user_id, error=str(e))
        return None

    async def set_session(self, user_id: str, history: List[dict]) -> None:
        """
        Saves a user's conversation history to Redis with an expiration time.

        Args:
            user_id: The unique identifier for the user.
            history: The conversation history (list of message dictionaries) to save.
        """
        key = self._get_session_key(user_id)
        try:
            serialized_history = json.dumps(history)
            await self.redis_client.set(key, serialized_history, ex=self.session_ttl)
        except RedisError as e:
            log.error("redis_set_session_error", user_id=user_id, error=str(e))

    async def delete_session(self, user_id: str) -> None:
        """
        Deletes a user's session from Redis.

        Args:
            user_id: The unique identifier for the user whose session should be deleted.
        """
        key = self._get_session_key(user_id)
        try:
            await self.redis_client.delete(key)
        except RedisError as e:
            log.error("redis_delete_session_error", user_id=user_id, error=str(e))


# Create a single, shared instance of the SessionManager.
# Other parts of the application will import this instance to use it.
session_manager = SessionManager()
