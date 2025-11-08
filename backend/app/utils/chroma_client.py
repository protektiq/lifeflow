"""Chroma vector database client"""
import chromadb
from chromadb.config import Settings
from typing import List, Optional
from app.config import settings
import uuid

# Initialize Chroma client
chroma_client = chromadb.HttpClient(
    host=settings.CHROMA_HOST,
    port=settings.CHROMA_PORT,
)

# Collection name for calendar events
COLLECTION_NAME = "calendar_events"


def get_collection():
    """Get or create the calendar events collection"""
    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist, create it
        collection = chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Calendar event embeddings for LifeFlow"}
        )
    return collection


def store_event_embedding(
    user_id: str,
    task_id: str,
    text: str,
    embedding: List[float],
    metadata: Optional[dict] = None
):
    """Store event embedding in Chroma"""
    collection = get_collection()
    
    metadata_dict = {
        "user_id": user_id,
        "task_id": task_id,
        "text": text,
        **(metadata or {}),
    }
    
    collection.add(
        ids=[f"{user_id}_{task_id}"],
        embeddings=[embedding],
        metadatas=[metadata_dict],
        documents=[text],
    )


def search_similar_events(
    user_id: str,
    query_embedding: List[float],
    n_results: int = 5
) -> List[dict]:
    """Search for similar events"""
    collection = get_collection()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where={"user_id": user_id},
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


def delete_event_embedding(user_id: str, task_id: str):
    """Delete event embedding"""
    collection = get_collection()
    collection.delete(ids=[f"{user_id}_{task_id}"])

