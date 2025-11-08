"""Notification models"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class Notification(BaseModel):
    """Notification model"""
    id: UUID
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    type: str = "nudge"
    message: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str = "pending"  # pending, sent, dismissed
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class NotificationCreate(BaseModel):
    """Notification creation model"""
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    type: str = "nudge"
    message: str
    scheduled_at: datetime
    status: str = "pending"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class NotificationResponse(BaseModel):
    """Notification response model"""
    id: UUID
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    type: str
    message: str
    scheduled_at: datetime
    sent_at: Optional[datetime] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

