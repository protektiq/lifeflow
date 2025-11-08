"""Task management API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.models.task import RawTaskResponse
from app.database import supabase
from app.api.auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


async def get_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get authenticated user from JWT token"""
    try:
        user = get_current_user(credentials.credentials)
        return user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.get("/raw", response_model=List[RawTaskResponse])
async def get_raw_tasks(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user = Depends(get_authenticated_user),
):
    """Get user's raw tasks"""
    try:
        query = supabase.table("raw_tasks").select("*").eq("user_id", user.id).order("start_time", desc=False)
        
        if start_date:
            query = query.gte("start_time", start_date)
        
        if end_date:
            query = query.lte("start_time", end_date)
        
        response = query.execute()
        
        tasks = []
        for task_data in response.data:
            tasks.append(RawTaskResponse(
            id=task_data["id"],
            user_id=task_data["user_id"],
            source=task_data["source"],
            title=task_data["title"],
            description=task_data.get("description"),
            start_time=datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00")),
            attendees=task_data.get("attendees", []),
            location=task_data.get("location"),
            recurrence_pattern=task_data.get("recurrence_pattern"),
            extracted_priority=task_data.get("extracted_priority"),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            created_at=datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00")),
        ))
        
        return tasks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch tasks: {str(e)}",
        )


@router.get("/raw/{task_id}", response_model=RawTaskResponse)
async def get_raw_task(
    task_id: str,
    user = Depends(get_authenticated_user),
):
    """Get a specific raw task by ID"""
    try:
        response = supabase.table("raw_tasks").select("*").eq("id", task_id).eq("user_id", user.id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        
        task_data = response.data[0]
        return RawTaskResponse(
            id=task_data["id"],
            user_id=task_data["user_id"],
            source=task_data["source"],
            title=task_data["title"],
            description=task_data.get("description"),
            start_time=datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00")),
            attendees=task_data.get("attendees", []),
            location=task_data.get("location"),
            recurrence_pattern=task_data.get("recurrence_pattern"),
            extracted_priority=task_data.get("extracted_priority"),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            created_at=datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task: {str(e)}",
        )


class TaskFlagsUpdate(BaseModel):
    """Task flags update model"""
    is_critical: Optional[bool] = None
    is_urgent: Optional[bool] = None


@router.patch("/raw/{task_id}", response_model=RawTaskResponse)
async def update_task_flags(
    task_id: str,
    flags: TaskFlagsUpdate,
    user = Depends(get_authenticated_user),
):
    """Update critical/urgent flags for a task"""
    try:
        # Verify task belongs to user
        existing = supabase.table("raw_tasks").select("*").eq(
            "id", task_id
        ).eq("user_id", user.id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        
        # Build update data
        update_data = {}
        if flags.is_critical is not None:
            update_data["is_critical"] = flags.is_critical
        if flags.is_urgent is not None:
            update_data["is_urgent"] = flags.is_urgent
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No flags provided to update",
            )
        
        # Update task
        response = supabase.table("raw_tasks").update(update_data).eq(
            "id", task_id
        ).execute()
        
        task_data = response.data[0]
        return RawTaskResponse(
            id=task_data["id"],
            user_id=task_data["user_id"],
            source=task_data["source"],
            title=task_data["title"],
            description=task_data.get("description"),
            start_time=datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00")),
            attendees=task_data.get("attendees", []),
            location=task_data.get("location"),
            recurrence_pattern=task_data.get("recurrence_pattern"),
            extracted_priority=task_data.get("extracted_priority"),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            created_at=datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}",
        )

