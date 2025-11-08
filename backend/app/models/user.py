"""User profile models"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserProfile(BaseModel):
    """User profile model"""
    id: UUID
    user_id: UUID
    energy_level: Optional[int] = None  # 1-5 scale
    preferences: Optional[dict] = {}
    created_at: datetime
    updated_at: datetime


class UserProfileCreate(BaseModel):
    """User profile creation model"""
    energy_level: Optional[int] = None
    preferences: Optional[dict] = {}


class UserProfileUpdate(BaseModel):
    """User profile update model"""
    energy_level: Optional[int] = None
    preferences: Optional[dict] = None

