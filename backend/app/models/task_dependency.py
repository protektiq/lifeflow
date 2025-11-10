"""Task Dependency models"""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class TaskDependency(BaseModel):
    """Task Dependency model - represents blocking relationships between tasks"""
    id: UUID
    task_id: UUID  # Task that is blocked
    blocked_by_task_id: UUID  # Task that blocks the other task
    dependency_type: str = Field(default="blocks", description="Type of dependency: 'blocks', 'depends_on', 'related_to'")
    user_id: UUID
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
    
    @validator('dependency_type')
    def validate_dependency_type(cls, v):
        """Validate dependency type"""
        allowed_types = ['blocks', 'depends_on', 'related_to']
        if v not in allowed_types:
            raise ValueError(f"dependency_type must be one of {allowed_types}")
        return v


class TaskDependencyCreate(BaseModel):
    """Task Dependency creation model"""
    task_id: UUID
    blocked_by_task_id: UUID
    dependency_type: str = Field(default="blocks", description="Type of dependency: 'blocks', 'depends_on', 'related_to'")
    
    @validator('dependency_type')
    def validate_dependency_type(cls, v):
        """Validate dependency type"""
        allowed_types = ['blocks', 'depends_on', 'related_to']
        if v not in allowed_types:
            raise ValueError(f"dependency_type must be one of {allowed_types}")
        return v
    
    @validator('blocked_by_task_id')
    def validate_not_same_task(cls, v, values):
        """Prevent a task from blocking itself"""
        if 'task_id' in values and v == values['task_id']:
            raise ValueError("A task cannot block itself")
        return v


class TaskDependencyResponse(BaseModel):
    """Task Dependency response model"""
    id: UUID
    task_id: UUID
    blocked_by_task_id: UUID
    dependency_type: str
    user_id: UUID
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }

