"""
Memory Service — conversation history management using Firestore.
"""
import uuid
import logging
from datetime import datetime
from typing import Optional
from firebase_admin import firestore

logger = logging.getLogger(__name__)


def get_db():
    return firestore.client()


async def get_or_create_conversation(
    dataset_id: str,
    user_id: str,
    conversation_id: Optional[str] = None,
) -> str:
    """Get existing or create new conversation. Returns conversation_id."""
    db = get_db()
    
    if conversation_id:
        doc_ref = db.collection('users').document(user_id).collection('conversations').document(conversation_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.id

    # Create new
    new_id = str(uuid.uuid4())
    doc_ref = db.collection('users').document(user_id).collection('conversations').document(new_id)
    doc_ref.set({
        'id': new_id,
        'user_id': user_id,
        'dataset_id': dataset_id,
        'title': "New Conversation",
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP,
    })
    return new_id


async def save_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
    code: Optional[str] = None,
    chart_path: Optional[str] = None,
    result_data: Optional[dict] = None,
) -> str:
    """Save a message to the conversation. Returns message_id."""
    db = get_db()
    msg_id = str(uuid.uuid4())
    
    doc_ref = db.collection('users').document(user_id).collection('conversations').document(conversation_id).collection('messages').document(msg_id)
    doc_ref.set({
        'id': msg_id,
        'conversation_id': conversation_id,
        'role': role,
        'content': content,
        'code': code,
        'chart_path': chart_path,
        'result_data': result_data,
        'created_at': firestore.SERVER_TIMESTAMP,
    })
    
    # Update conversation updated_at
    db.collection('users').document(user_id).collection('conversations').document(conversation_id).update({
        'updated_at': firestore.SERVER_TIMESTAMP
    })
    
    return msg_id


async def get_conversation_history(
    conversation_id: str,
    user_id: str,
    limit: int = 20,
) -> list[dict]:
    """Get recent messages from a conversation."""
    db = get_db()
    messages_ref = db.collection('users').document(user_id).collection('conversations').document(conversation_id).collection('messages')
    
    query = messages_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit)
    docs = query.stream()
    
    messages = []
    for doc in docs:
        data = doc.to_dict()
        messages.append({
            "role": data.get("role"),
            "content": data.get("content"),
            "code": data.get("code")
        })
        
    # Return in chronological order
    return list(reversed(messages))


async def update_conversation_title(
    conversation_id: str,
    user_id: str,
    first_message: str,
):
    """Auto-generate conversation title from first message."""
    title = first_message[:50] + ("..." if len(first_message) > 50 else "")
    db = get_db()
    
    doc_ref = db.collection('users').document(user_id).collection('conversations').document(conversation_id)
    doc = doc_ref.get()
    
    if doc.exists and doc.to_dict().get("title") == "New Conversation":
        doc_ref.update({
            'title': title,
            'updated_at': firestore.SERVER_TIMESTAMP
        })
