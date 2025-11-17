from typing import Any, Dict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import CollectedData, User


class DataRepository:
    """
    Handles database operations for creating records.
    """

    async def create_user(self, db: AsyncSession, *, whatsapp_id: str) -> User:
        """
        Creates a new user in the database.

        Args:
            db: The asynchronous database session.
            whatsapp_id: The user's WhatsApp ID.

        Returns:
            The newly created User object.
        """
        new_user = User(whatsapp_id=whatsapp_id)
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    async def create_collected_data(
        self,
        db: AsyncSession,
        *,
        user_id: UUID,
        conversation_id: UUID,
        data: Dict[str, Any],
    ) -> CollectedData:
        """
        Creates a new collected_data record in the database.

        Args:
            db: The asynchronous database session.
            user_id: The ID of the user associated with this data.
            conversation_id: The ID of the conversation where data was collected.
            data: The JSON data collected from the user.

        Returns:
            The newly created CollectedData object.
        """
        new_data = CollectedData(
            user_id=user_id, conversation_id=conversation_id, data=data
        )
        db.add(new_data)
        await db.commit()
        await db.refresh(new_data)
        return new_data


data_repository = DataRepository()
