"""Task feedback API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from uuid import UUID
from app.database import supabase
from app.api.auth import get_current_user
from app.models.task_feedback import TaskFeedbackCreate, TaskFeedbackResponse
from app.utils.monitoring import StructuredLogger
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


class TaskDoneRequest(BaseModel):
    """Request model for marking task as done"""
    plan_id: Optional[str] = None


class TaskSnoozeRequest(BaseModel):
    """Request model for snoozing task"""
    duration_minutes: int = 15
    plan_id: Optional[str] = None


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


async def validate_task_belongs_to_user(task_id: str, user_id: str) -> bool:
    """Validate that task belongs to user"""
    try:
        response = supabase.table("raw_tasks").select("id").eq("id", task_id).eq("user_id", user_id).execute()
        return len(response.data) > 0
    except Exception:
        return False


@router.post("/task/{task_id}/done", response_model=TaskFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def mark_task_done(
    task_id: str,
    request: TaskDoneRequest,
    user = Depends(get_authenticated_user),
):
    """Mark a task as done"""
    try:
        # Validate task belongs to user
        if not await validate_task_belongs_to_user(task_id, user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or does not belong to user",
            )
        
        # Create feedback record
        feedback_data = {
            "user_id": user.id,
            "task_id": task_id,
            "plan_id": request.plan_id,
            "action": "done",
            "snooze_duration_minutes": None,
        }
        
        response = supabase.table("task_feedback").insert(feedback_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create feedback record",
            )
        
        data = response.data[0]
        
        # Update task status in daily_plans if plan_id provided
        if request.plan_id:
            try:
                # Get the plan
                plan_response = supabase.table("daily_plans").select("tasks").eq("id", request.plan_id).eq("user_id", user.id).execute()
                
                if plan_response.data:
                    tasks = plan_response.data[0].get("tasks", [])
                    # Update task status in tasks array
                    updated_tasks = []
                    for task in tasks:
                        if str(task.get("task_id")) == task_id:
                            task["status"] = "done"
                            task["completed_at"] = datetime.utcnow().isoformat()
                        updated_tasks.append(task)
                    
                    # Update plan
                    supabase.table("daily_plans").update({
                        "tasks": updated_tasks,
                        "updated_at": datetime.utcnow().isoformat(),
                    }).eq("id", request.plan_id).execute()
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"function": "mark_task_done", "task_id": task_id, "plan_id": request.plan_id},
                )
                # Don't fail the request if plan update fails
        
        StructuredLogger.log_event(
            "task_marked_done",
            f"Task {task_id} marked as done",
            user_id=user.id,
            metadata={"task_id": task_id, "plan_id": request.plan_id},
        )
        
        return TaskFeedbackResponse(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            task_id=UUID(data["task_id"]),
            plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
            action=data["action"],
            snooze_duration_minutes=data.get("snooze_duration_minutes"),
            feedback_at=datetime.fromisoformat(data["feedback_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "mark_task_done", "task_id": task_id, "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark task as done: {str(e)}",
        )


@router.post("/task/{task_id}/snooze", response_model=TaskFeedbackResponse, status_code=status.HTTP_201_CREATED)
async def snooze_task(
    task_id: str,
    request: TaskSnoozeRequest,
    user = Depends(get_authenticated_user),
):
    """Snooze a task for a specified duration"""
    try:
        # Validate task belongs to user
        if not await validate_task_belongs_to_user(task_id, user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or does not belong to user",
            )
        
        # Validate duration
        if request.duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be positive",
            )
        
        # Create feedback record
        feedback_data = {
            "user_id": user.id,
            "task_id": task_id,
            "plan_id": request.plan_id,
            "action": "snoozed",
            "snooze_duration_minutes": request.duration_minutes,
        }
        
        response = supabase.table("task_feedback").insert(feedback_data).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create feedback record",
            )
        
        data = response.data[0]
        
        # Update task status in daily_plans if plan_id provided
        if request.plan_id:
            try:
                # Get the plan
                plan_response = supabase.table("daily_plans").select("tasks").eq("id", request.plan_id).eq("user_id", user.id).execute()
                
                if plan_response.data:
                    tasks = plan_response.data[0].get("tasks", [])
                    # Update task predicted_start time
                    updated_tasks = []
                    for task in tasks:
                        if str(task.get("task_id")) == task_id:
                            # Calculate new start time
                            original_start = datetime.fromisoformat(task.get("predicted_start").replace("Z", "+00:00"))
                            new_start = original_start + timedelta(minutes=request.duration_minutes)
                            
                            # Calculate duration
                            original_end = datetime.fromisoformat(task.get("predicted_end").replace("Z", "+00:00"))
                            duration = original_end - original_start
                            new_end = new_start + duration
                            
                            task["predicted_start"] = new_start.isoformat()
                            task["predicted_end"] = new_end.isoformat()
                            task["status"] = "snoozed"
                            task["snoozed_at"] = datetime.utcnow().isoformat()
                            task["snooze_duration_minutes"] = request.duration_minutes
                        updated_tasks.append(task)
                    
                    # Update plan
                    supabase.table("daily_plans").update({
                        "tasks": updated_tasks,
                        "updated_at": datetime.utcnow().isoformat(),
                    }).eq("id", request.plan_id).execute()
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"function": "snooze_task", "task_id": task_id, "plan_id": request.plan_id},
                )
                # Don't fail the request if plan update fails
        
        StructuredLogger.log_event(
            "task_snoozed",
            f"Task {task_id} snoozed for {request.duration_minutes} minutes",
            user_id=user.id,
            metadata={
                "task_id": task_id,
                "plan_id": request.plan_id,
                "duration_minutes": request.duration_minutes,
            },
        )
        
        return TaskFeedbackResponse(
            id=UUID(data["id"]),
            user_id=UUID(data["user_id"]),
            task_id=UUID(data["task_id"]),
            plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
            action=data["action"],
            snooze_duration_minutes=data.get("snooze_duration_minutes"),
            feedback_at=datetime.fromisoformat(data["feedback_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "snooze_task", "task_id": task_id, "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to snooze task: {str(e)}",
        )


@router.get("/task/{task_id}", response_model=List[TaskFeedbackResponse])
async def get_task_feedback(
    task_id: str,
    user = Depends(get_authenticated_user),
):
    """Get feedback history for a task"""
    try:
        # Validate task belongs to user
        if not await validate_task_belongs_to_user(task_id, user.id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or does not belong to user",
            )
        
        response = supabase.table("task_feedback").select("*").eq(
            "task_id", task_id
        ).eq("user_id", user.id).order("created_at", desc=True).execute()
        
        feedback_list = []
        for data in response.data:
            feedback_list.append(TaskFeedbackResponse(
                id=UUID(data["id"]),
                user_id=UUID(data["user_id"]),
                task_id=UUID(data["task_id"]),
                plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
                action=data["action"],
                snooze_duration_minutes=data.get("snooze_duration_minutes"),
                feedback_at=datetime.fromisoformat(data["feedback_at"].replace("Z", "+00:00")),
                created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            ))
        
        return feedback_list
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_task_feedback", "task_id": task_id, "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task feedback: {str(e)}",
        )

