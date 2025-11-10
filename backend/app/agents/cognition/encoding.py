"""Context vectorization service for Priority + Energy Level"""
from typing import List, Optional, Dict
from openai import OpenAI
from app.config import settings
from app.utils.chroma_client import chroma_client
from datetime import date, datetime
import json


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Collection name for task context embeddings
CONTEXT_COLLECTION_NAME = "task_context_embeddings"

# Collection name for short text contexts (email snippets, task notes)
SHORT_TEXT_COLLECTION_NAME = "short_text_contexts"


def get_context_collection():
    """Get or create the task context embeddings collection"""
    try:
        collection = chroma_client.get_collection(name=CONTEXT_COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist, create it
        collection = chroma_client.create_collection(
            name=CONTEXT_COLLECTION_NAME,
            metadata={"description": "Task context embeddings with Priority + Energy Level"}
        )
    return collection


def create_task_context_embedding(
    raw_task: dict,
    energy_level: int,
    priority: Optional[str] = None
) -> List[float]:
    """
    Create context embedding combining task metadata with energy level
    
    Args:
        raw_task: Raw task dictionary with title, description, etc.
        energy_level: User's energy level (1-5)
        priority: Task priority (extracted_priority)
    
    Returns:
        Embedding vector as list of floats
    """
    # Build context text combining task info with energy level
    task_title = raw_task.get("title", "")
    task_description = raw_task.get("description", "") or ""
    task_priority = priority or raw_task.get("extracted_priority", "normal")
    
    # Create context string
    context_text = f"""
    Task: {task_title}
    Description: {task_description}
    Priority: {task_priority}
    Energy Level Context: {energy_level}/5
    Critical: {raw_task.get('is_critical', False)}
    Urgent: {raw_task.get('is_urgent', False)}
    """.strip()
    
    # Generate embedding using OpenAI
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=context_text
    )
    
    return response.data[0].embedding


def store_task_context_embedding(
    user_id: str,
    task_id: str,
    raw_task: dict,
    energy_level: int,
    priority: Optional[str] = None,
    plan_date: Optional[date] = None,
    metadata: Optional[Dict] = None
):
    """
    Store task context embedding in Chroma
    
    Args:
        user_id: User UUID
        task_id: Task UUID
        raw_task: Raw task dictionary
        energy_level: Energy level (1-5)
        priority: Task priority
        plan_date: Date for the plan
        metadata: Additional metadata
    """
    collection = get_context_collection()
    
    # Generate embedding
    embedding = create_task_context_embedding(raw_task, energy_level, priority)
    
    # Build context text for document storage
    task_title = raw_task.get("title", "")
    task_description = raw_task.get("description", "") or ""
    context_text = f"Task: {task_title}\nDescription: {task_description}\nPriority: {priority or 'normal'}\nEnergy Level: {energy_level}/5"
    
    # Prepare metadata - filter out None values as ChromaDB doesn't accept them
    metadata_dict = {
        "user_id": str(user_id),
        "task_id": str(task_id),
        "energy_level": energy_level,
        "priority": str(priority or raw_task.get("extracted_priority") or "normal"),
        "is_critical": bool(raw_task.get("is_critical", False)),
        "is_urgent": bool(raw_task.get("is_urgent", False)),
    }
    
    # Add additional metadata, filtering out None values
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                # Convert to string if not a basic type
                if isinstance(value, (str, int, float, bool)):
                    metadata_dict[key] = value
                else:
                    metadata_dict[key] = str(value)
    
    if plan_date:
        metadata_dict["plan_date"] = plan_date.isoformat()
    
    # Final filter to ensure no None values
    metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}
    
    # Store in Chroma
    collection.add(
        ids=[f"{user_id}_{task_id}_{plan_date.isoformat() if plan_date else 'default'}"],
        embeddings=[embedding],
        metadatas=[metadata_dict],
        documents=[context_text],
    )


def search_similar_task_contexts(
    user_id: str,
    query_embedding: List[float],
    energy_level: Optional[int] = None,
    n_results: int = 5
) -> List[dict]:
    """
    Search for similar task contexts
    
    Args:
        user_id: User UUID
        query_embedding: Query embedding vector
        energy_level: Optional energy level filter
        n_results: Number of results to return
    
    Returns:
        List of similar task contexts
    """
    collection = get_context_collection()
    
    # Build where clause
    where_clause = {"user_id": str(user_id)}
    if energy_level:
        where_clause["energy_level"] = energy_level
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_clause,
    )
    
    return [
        {
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i] if "distances" in results else None,
            "metadata": results["metadatas"][0][i] if "metadatas" in results else {},
            "document": results["documents"][0][i] if "documents" in results else "",
        }
        for i in range(len(results["ids"][0]))
    ]


def get_short_text_collection():
    """Get or create the short text contexts collection"""
    try:
        collection = chroma_client.get_collection(name=SHORT_TEXT_COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist, create it
        collection = chroma_client.create_collection(
            name=SHORT_TEXT_COLLECTION_NAME,
            metadata={"description": "Short text context embeddings (email snippets, task notes) for LifeFlow"}
        )
    return collection


def create_short_text_embedding(text: str) -> List[float]:
    """
    Create embedding for short text contexts (email snippets, task notes)
    
    Args:
        text: Short text to embed (email snippet or task note)
    
    Returns:
        Embedding vector as list of floats
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Generate embedding using OpenAI
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text.strip()
    )
    
    return response.data[0].embedding


def store_email_snippet_embedding(
    user_id: str,
    task_id: str,
    email_id: str,
    snippet: str,
    thread_id: Optional[str] = None,
    metadata: Optional[Dict] = None
):
    """
    Store email snippet embedding in Chroma
    
    Args:
        user_id: User UUID
        task_id: Task UUID (if task was created from email)
        email_id: Email message ID
        snippet: Email snippet text
        thread_id: Optional email thread ID for conversation grouping
        metadata: Additional metadata
    """
    if not snippet or not snippet.strip():
        return  # Skip empty snippets
    
    collection = get_short_text_collection()
    
    # Generate embedding
    embedding = create_short_text_embedding(snippet)
    
    # Prepare metadata - filter out None values as ChromaDB doesn't accept them
    metadata_dict = {
        "user_id": str(user_id),
        "task_id": str(task_id),
        "email_id": str(email_id),
        "source_type": "email_snippet",
    }
    
    if thread_id:
        metadata_dict["thread_id"] = str(thread_id)
    
    # Add additional metadata, filtering out None values
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                # Convert to string if not a basic type
                if isinstance(value, (str, int, float, bool)):
                    metadata_dict[key] = value
                else:
                    metadata_dict[key] = str(value)
    
    # Add timestamp
    metadata_dict["timestamp"] = datetime.utcnow().isoformat()
    
    # Final filter to ensure no None values
    metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}
    
    # Create unique ID for this embedding
    embedding_id = f"{user_id}_{email_id}_{task_id}"
    
    # Store in Chroma
    collection.add(
        ids=[embedding_id],
        embeddings=[embedding],
        metadatas=[metadata_dict],
        documents=[snippet],
    )


def store_task_note_embedding(
    user_id: str,
    task_id: str,
    note_text: str,
    metadata: Optional[Dict] = None
):
    """
    Store task note/description embedding in Chroma
    
    Args:
        user_id: User UUID
        task_id: Task UUID
        note_text: Task note or description text
        metadata: Additional metadata
    """
    if not note_text or not note_text.strip():
        return  # Skip empty notes
    
    collection = get_short_text_collection()
    
    # Generate embedding
    embedding = create_short_text_embedding(note_text)
    
    # Prepare metadata - filter out None values as ChromaDB doesn't accept them
    metadata_dict = {
        "user_id": str(user_id),
        "task_id": str(task_id),
        "source_type": "task_note",
    }
    
    # Add additional metadata, filtering out None values
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                # Convert to string if not a basic type
                if isinstance(value, (str, int, float, bool)):
                    metadata_dict[key] = value
                else:
                    metadata_dict[key] = str(value)
    
    # Add timestamp
    metadata_dict["timestamp"] = datetime.utcnow().isoformat()
    
    # Final filter to ensure no None values
    metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}
    
    # Create unique ID for this embedding
    embedding_id = f"{user_id}_{task_id}_note"
    
    # Store in Chroma
    collection.add(
        ids=[embedding_id],
        embeddings=[embedding],
        metadatas=[metadata_dict],
        documents=[note_text],
    )


def store_conversation_embedding(
    user_id: str,
    thread_id: str,
    conversation_text: str,
    email_ids: Optional[List[str]] = None,
    task_ids: Optional[List[str]] = None,
    metadata: Optional[Dict] = None
):
    """
    Store email thread/conversation embedding in Chroma
    
    Args:
        user_id: User UUID
        thread_id: Email thread ID
        conversation_text: Combined text from conversation thread
        email_ids: List of email IDs in the thread
        task_ids: List of task IDs related to this conversation
        metadata: Additional metadata
    """
    if not conversation_text or not conversation_text.strip():
        return  # Skip empty conversations
    
    collection = get_short_text_collection()
    
    # Generate embedding
    embedding = create_short_text_embedding(conversation_text)
    
    # Prepare metadata - filter out None values as ChromaDB doesn't accept them
    metadata_dict = {
        "user_id": str(user_id),
        "thread_id": str(thread_id),
        "source_type": "conversation",
    }
    
    if email_ids:
        metadata_dict["email_ids"] = ",".join([str(eid) for eid in email_ids])
    
    if task_ids:
        metadata_dict["task_ids"] = ",".join([str(tid) for tid in task_ids])
    
    # Add additional metadata, filtering out None values
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                # Convert to string if not a basic type
                if isinstance(value, (str, int, float, bool)):
                    metadata_dict[key] = value
                else:
                    metadata_dict[key] = str(value)
    
    # Add timestamp
    metadata_dict["timestamp"] = datetime.utcnow().isoformat()
    
    # Final filter to ensure no None values
    metadata_dict = {k: v for k, v in metadata_dict.items() if v is not None}
    
    # Create unique ID for this embedding
    embedding_id = f"{user_id}_{thread_id}_conversation"
    
    # Store in Chroma
    collection.add(
        ids=[embedding_id],
        embeddings=[embedding],
        metadatas=[metadata_dict],
        documents=[conversation_text],
    )


def search_similar_short_texts(
    user_id: str,
    query_embedding: List[float],
    source_type: Optional[str] = None,
    n_results: int = 5
) -> List[dict]:
    """
    Search for similar short text contexts
    
    Args:
        user_id: User UUID
        query_embedding: Query embedding vector
        source_type: Optional filter by source_type ("email_snippet", "task_note", "conversation")
        n_results: Number of results to return
    
    Returns:
        List of similar short text contexts
    """
    collection = get_short_text_collection()
    
    # Build where clause
    where_clause = {"user_id": str(user_id)}
    if source_type:
        where_clause["source_type"] = source_type
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_clause,
    )
    
    return [
        {
            "id": results["ids"][0][i],
            "distance": results["distances"][0][i] if "distances" in results else None,
            "metadata": results["metadatas"][0][i] if "metadatas" in results else {},
            "document": results["documents"][0][i] if "documents" in results else "",
        }
        for i in range(len(results["ids"][0]))
    ]

