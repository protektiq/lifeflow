"""Daily Plan models"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from uuid import UUID


class DailyPlanTask(BaseModel):
    """Individual task in a daily plan"""
    task_id: UUID
    predicted_start: datetime
    predicted_end: datetime
    priority_score: float
    title: str
    is_critical: bool = False
    is_urgent: bool = False


class DailyPlan(BaseModel):
    """Complete daily plan"""
    id: Optional[UUID] = None
    user_id: UUID
    plan_date: date
    tasks: List[DailyPlanTask]
    energy_level: Optional[int] = None
    status: str = "active"
    generated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class PlanningContext(BaseModel):
    """Input context for planning"""
    raw_tasks: List[dict]  # List of RawTask dictionaries
    energy_level: int
    plan_date: date
    time_constraints: Optional[dict] = None  # Optional global time constraints
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
        }


class DailyPlanCreate(BaseModel):
    """Daily plan creation model"""
    user_id: UUID
    plan_date: date
    tasks: List[DailyPlanTask]
    energy_level: Optional[int] = None
    status: str = "active"


class DailyPlanResponse(BaseModel):
    """Daily plan response model"""
    id: UUID
    user_id: UUID
    plan_date: date
    tasks: List[dict]  # JSONB from database
    energy_level: Optional[int] = None
    status: str
    generated_at: datetime
    created_at: datetime
    updated_at: datetime

