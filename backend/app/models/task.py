"""Raw Task models"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import json


class RawTask(BaseModel):
    """Raw Task model - standardized format for ingested calendar events"""
    id: UUID
    user_id: UUID
    source: str  # "google_calendar", "todoist", etc.
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    recurrence_pattern: Optional[str] = None
    extracted_priority: Optional[str] = None
    is_critical: bool = False
    is_urgent: bool = False
    is_spam: bool = False
    spam_reason: Optional[str] = None
    spam_score: Optional[float] = None
    raw_data: dict  # Original event data as JSON
    created_at: datetime
    # Sync tracking fields
    external_id: Optional[str] = None
    sync_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    sync_direction: Optional[str] = None
    external_updated_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    # Completion tracking fields
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    # Completion tracking fields
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class RawTaskCreate(BaseModel):
    """Raw Task creation model"""
    source: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    recurrence_pattern: Optional[str] = None
    extracted_priority: Optional[str] = None
    is_critical: bool = False
    is_urgent: bool = False
    is_spam: bool = False
    spam_reason: Optional[str] = None
    spam_score: Optional[float] = None
    raw_data: dict
    # Sync tracking fields
    external_id: Optional[str] = None
    sync_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    sync_direction: Optional[str] = None
    external_updated_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    # Completion tracking fields
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    # Completion tracking fields
    is_completed: bool = False
    completed_at: Optional[datetime] = None


class RawTaskResponse(BaseModel):
    """Raw Task response model"""
    id: UUID
    user_id: UUID
    source: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    recurrence_pattern: Optional[str] = None
    extracted_priority: Optional[str] = None
    is_critical: bool = False
    is_urgent: bool = False
    is_spam: bool = False
    spam_reason: Optional[str] = None
    spam_score: Optional[float] = None
    created_at: datetime
    # Sync tracking fields
    external_id: Optional[str] = None
    sync_status: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    sync_direction: Optional[str] = None
    external_updated_at: Optional[datetime] = None
    sync_error: Optional[str] = None
    # Completion tracking fields
    is_completed: bool = False
    completed_at: Optional[datetime] = None

