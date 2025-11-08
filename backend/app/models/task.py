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
    source: str  # "google_calendar"
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: List[str] = []
    location: Optional[str] = None
    recurrence_pattern: Optional[str] = None
    extracted_priority: Optional[str] = None
    raw_data: dict  # Original event data as JSON
    created_at: datetime
    
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
    raw_data: dict


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
    created_at: datetime

