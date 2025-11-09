"""Reminders API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
from app.database import supabase
from app.api.auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.utils.monitoring import StructuredLogger

router = APIRouter()
security = HTTPBearer()


class ReminderResponse(BaseModel):
    """Reminder response model"""
    id: str
    title: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    is_all_day: bool
    date: str


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


def is_reminder_event(task_data: dict, raw_data: dict) -> bool:
    """Check if a task is a reminder"""
    event_type = raw_data.get("eventType", "default")
    start_data = raw_data.get("start", {})
    is_all_day_event = "date" in start_data
    
    start_time = datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00"))
    duration = end_time - start_time
    
    title_lower = task_data.get("title", "").lower()
    has_attendees = task_data.get("attendees") and len(task_data.get("attendees", [])) > 0
    has_location = bool(task_data.get("location"))
    
    return (
        event_type == "reminder" or
        (is_all_day_event and not has_attendees and not has_location) or
        (duration.total_seconds() < 300 and
         not has_attendees and
         not has_location and
         "reminder" in title_lower)
    )


@router.get("/{target_date}", response_model=List[ReminderResponse])
async def get_reminders_for_date(
    target_date: str,
    user = Depends(get_authenticated_user),
):
    """Get reminders for a specific date"""
    try:
        plan_date = date.fromisoformat(target_date)
        plan_date_str = plan_date.isoformat()
        
        # Query range: from start of plan_date UTC to start of day_after_next UTC
        from datetime import timedelta
        day_after_next = plan_date + timedelta(days=2)
        start_query = f"{plan_date_str}T00:00:00Z"
        end_query = f"{day_after_next.isoformat()}T00:00:00Z"
        
        tasks_response = supabase.table("raw_tasks").select("*").eq(
            "user_id", user.id
        ).gte("start_time", start_query).lt("start_time", end_query).execute()
        
        reminders = []
        
        for task_data in tasks_response.data:
            raw_data = task_data.get("raw_data", {})
            start_data = raw_data.get("start", {})
            
            # Skip if already converted to task
            if raw_data.get("converted_from_reminder"):
                continue
            
            if not is_reminder_event(task_data, raw_data):
                continue
            
            # Check if reminder is for the plan_date
            is_all_day_event = "date" in start_data
            reminder_date_matches = False
            reminder_date = None
            
            if is_all_day_event:
                all_day_date_str = start_data.get("date")
                if all_day_date_str:
                    reminder_date = date.fromisoformat(all_day_date_str)
                    reminder_date_matches = reminder_date == plan_date
            else:
                # For timed reminders, check local date
                date_time_str = start_data.get("dateTime", "")
                if date_time_str:
                    try:
                        date_part = date_time_str.split('T')[0]
                        if len(date_part) == 10:
                            reminder_date = date.fromisoformat(date_part)
                            reminder_date_matches = reminder_date == plan_date
                    except (ValueError, AttributeError, IndexError):
                        # Fallback to UTC date check
                        start_time = datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00"))
                        reminder_date = start_time.date()
                        reminder_date_matches = reminder_date == plan_date or reminder_date == plan_date + timedelta(days=1)
            
            if reminder_date_matches:
                reminders.append(ReminderResponse(
                    id=str(task_data.get("id")),
                    title=task_data.get("title"),
                    description=task_data.get("description"),
                    start_time=task_data.get("start_time"),
                    end_time=task_data.get("end_time"),
                    is_all_day=is_all_day_event,
                    date=reminder_date.isoformat() if reminder_date else plan_date_str,
                ))
        
        return reminders
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}",
        )
    except Exception as e:
        StructuredLogger.log_error(e, context={"function": "get_reminders_for_date", "user_id": user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch reminders: {str(e)}",
        )


@router.post("/{reminder_id}/convert-to-task")
async def convert_reminder_to_task(
    reminder_id: str,
    user = Depends(get_authenticated_user),
):
    """Convert a reminder to a task by updating its metadata"""
    try:
        # Fetch the reminder task
        response = supabase.table("raw_tasks").select("*").eq(
            "id", reminder_id
        ).eq("user_id", user.id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reminder not found",
            )
        
        task_data = response.data[0]
        raw_data = task_data.get("raw_data", {})
        
        # Mark as converted by adding a flag to raw_data
        raw_data["converted_from_reminder"] = True
        raw_data["converted_at"] = datetime.utcnow().isoformat()
        
        # Update the task in database
        supabase.table("raw_tasks").update({
            "raw_data": raw_data,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", reminder_id).execute()
        
        StructuredLogger.log_event(
            "reminder_converted_to_task",
            f"Converted reminder '{task_data.get('title')}' to task",
            user_id=user.id,
            metadata={"reminder_id": reminder_id, "task_title": task_data.get("title")},
        )
        
        return {
            "success": True,
            "message": "Reminder converted to task successfully",
            "task_id": reminder_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(e, context={"function": "convert_reminder_to_task", "user_id": user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert reminder: {str(e)}",
        )

