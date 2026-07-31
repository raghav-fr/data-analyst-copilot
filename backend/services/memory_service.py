"""
Memory Service — conversation history management using SQLite.
"""
import uuid
import logging
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import Conversation, Message

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    db: AsyncSession,
    dataset_id: str,
    conversation_id: Optional[str] = None,
) -> str:
    """Get existing or create new conversation. Returns conversation_id."""
    from typing import Optional

    if conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv.id

    # Create new
    new_conv = Conversation(
        id=str(uuid.uuid4()),
        dataset_id=dataset_id,
        title="New Conversation",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(new_conv)
    await db.commit()
    return new_conv.id


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    code: Optional[str] = None,
    chart_path: Optional[str] = None,
    result_data: Optional[dict] = None,
) -> str:
    """Save a message to the conversation. Returns message_id."""
    from typing import Optional
    msg = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        code=code,
        chart_path=chart_path,
        result_data=result_data,
        created_at=datetime.utcnow(),
    )
    db.add(msg)
    await db.commit()
    return msg.id


async def get_conversation_history(
    db: AsyncSession,
    conversation_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get recent messages from a conversation."""
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    # Return in chronological order
    return [
        {"role": msg.role, "content": msg.content, "code": msg.code}
        for msg in reversed(messages)
    ]


async def update_conversation_title(
    db: AsyncSession,
    conversation_id: str,
    first_message: str,
):
    """Auto-generate conversation title from first message."""
    title = first_message[:50] + ("..." if len(first_message) > 50 else "")
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv and conv.title == "New Conversation":
        conv.title = title
        conv.updated_at = datetime.utcnow()
        await db.commit()


from typing import Optional
