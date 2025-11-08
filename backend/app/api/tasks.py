"""Task management API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import datetime
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
                created_at=datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00")),
            ))
        
        return {"tasks": tasks}
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
            created_at=datetime.fromisoformat(task_data["created_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task: {str(e)}",
        )

