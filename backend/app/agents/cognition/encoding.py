"""Context vectorization service for Priority + Energy Level"""
from typing import List, Optional, Dict
from openai import OpenAI
from app.config import settings
from app.utils.chroma_client import chroma_client
from datetime import date
import json


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Collection name for task context embeddings
CONTEXT_COLLECTION_NAME = "task_context_embeddings"


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

