"""Task feedback models"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class TaskFeedback(BaseModel):
    """Task feedback model"""
    id: UUID
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    action: str  # done or snoozed
    snooze_duration_minutes: Optional[int] = None
    feedback_at: datetime
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class TaskFeedbackCreate(BaseModel):
    """Task feedback creation model"""
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    action: str  # done or snoozed
    snooze_duration_minutes: Optional[int] = None
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v)
        }


class TaskFeedbackResponse(BaseModel):
    """Task feedback response model"""
    id: UUID
    user_id: UUID
    task_id: UUID
    plan_id: Optional[UUID] = None
    action: str
    snooze_duration_minutes: Optional[int] = None
    feedback_at: datetime
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

