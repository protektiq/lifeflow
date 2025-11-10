"""Daily Plan API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel
from app.database import supabase
from app.api.auth import get_current_user
from app.models.plan import DailyPlan, DailyPlanTask, PlanningContext, DailyPlanResponse
from app.agents.cognition.planner import generate_daily_plan
from app.agents.cognition.encoding import store_task_context_embedding
from app.agents.orchestration.workflow import run_planning_workflow
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import json

router = APIRouter()
security = HTTPBearer()


def filter_spam_tasks_from_plan(tasks: List[dict], user_id: str) -> List[dict]:
    """Filter out spam tasks from a plan's task list"""
    if not tasks:
        return tasks
    
    # Get task IDs from plan tasks
    task_ids = [task.get("task_id") for task in tasks if task.get("task_id")]
    
    if not task_ids:
        return tasks
    
    # Check which tasks are spam
    spam_check = supabase.table("raw_tasks").select("id, is_spam").in_(
        "id", task_ids
    ).eq("user_id", user_id).execute()
    
    # Create set of spam task IDs (handle both True and NULL/False)
    spam_task_ids = {
        str(task["id"]) for task in spam_check.data 
        if task.get("is_spam") is True  # Explicitly check for True (not just truthy)
    }
    
    # Filter out spam tasks
    filtered_tasks = [
        task for task in tasks 
        if str(task.get("task_id")) not in spam_task_ids
    ]
    
    return filtered_tasks


class PlanGenerateRequest(BaseModel):
    """Plan generation request"""
    plan_date: date


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


@router.post("/generate", response_model=DailyPlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_plan(
    request: PlanGenerateRequest,
    user = Depends(get_authenticated_user),
):
    """Generate daily plan for a specific date"""
    try:
        # Run planning workflow
        result = await run_planning_workflow(user.id, request.plan_date)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate plan: {result.get('errors', ['Unknown error'])}",
            )
        
        # Fetch the generated plan from database
        response = supabase.table("daily_plans").select("*").eq(
            "user_id", user.id
        ).eq("plan_date", request.plan_date.isoformat()).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan was generated but not found in database",
            )
        
        plan_data = response.data[0]
        
        # Filter out spam tasks from the plan
        tasks = filter_spam_tasks_from_plan(plan_data.get("tasks", []), user.id)
        
        return DailyPlanResponse(
            id=plan_data["id"],
            user_id=plan_data["user_id"],
            plan_date=date.fromisoformat(plan_data["plan_date"]),
            tasks=tasks,
            energy_level=plan_data.get("energy_level"),
            status=plan_data["status"],
            generated_at=datetime.fromisoformat(plan_data["generated_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(plan_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(plan_data["updated_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {str(e)}",
        )


@router.get("/{target_date}", response_model=Optional[DailyPlanResponse])
async def get_plan_for_date(
    target_date: str,
    user = Depends(get_authenticated_user),
):
    """Get plan for a specific date"""
    try:
        response = supabase.table("daily_plans").select("*").eq(
            "user_id", user.id
        ).eq("plan_date", target_date).execute()
        
        if not response.data:
            return None
        
        plan_data = response.data[0]
        
        # Filter out spam tasks from the plan
        tasks = filter_spam_tasks_from_plan(plan_data.get("tasks", []), user.id)
        
        return DailyPlanResponse(
            id=plan_data["id"],
            user_id=plan_data["user_id"],
            plan_date=date.fromisoformat(plan_data["plan_date"]),
            tasks=tasks,
            energy_level=plan_data.get("energy_level"),
            status=plan_data["status"],
            generated_at=datetime.fromisoformat(plan_data["generated_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(plan_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(plan_data["updated_at"].replace("Z", "+00:00")),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plan: {str(e)}",
        )


@router.get("", response_model=List[DailyPlanResponse])
async def get_plans(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format YYYY-MM-DD)"),
    user = Depends(get_authenticated_user),
):
    """List plans with date range filter"""
    try:
        query = supabase.table("daily_plans").select("*").eq(
            "user_id", user.id
        ).order("plan_date", desc=False)
        
        if start_date:
            query = query.gte("plan_date", start_date)
        
        if end_date:
            query = query.lte("plan_date", end_date)
        
        response = query.execute()
        
        # Filter spam tasks from all plans
        return [
            DailyPlanResponse(
                id=item["id"],
                user_id=item["user_id"],
                plan_date=date.fromisoformat(item["plan_date"]),
                tasks=filter_spam_tasks_from_plan(item.get("tasks", []), user.id),
                energy_level=item.get("energy_level"),
                status=item["status"],
                generated_at=datetime.fromisoformat(item["generated_at"].replace("Z", "+00:00")),
                created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
            )
            for item in response.data
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch plans: {str(e)}",
        )


@router.put("/{plan_id}", response_model=DailyPlanResponse)
async def update_plan_status(
    plan_id: str,
    status: str = Query(..., description="New status for the plan"),
    user = Depends(get_authenticated_user),
):
    """Update plan status"""
    try:
        # Verify plan belongs to user
        existing = supabase.table("daily_plans").select("*").eq(
            "id", plan_id
        ).eq("user_id", user.id).execute()
        
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan not found",
            )
        
        # Update status
        response = supabase.table("daily_plans").update({
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", plan_id).execute()
        
        plan_data = response.data[0]
        
        # Filter out spam tasks from the plan
        tasks = filter_spam_tasks_from_plan(plan_data.get("tasks", []), user.id)
        
        return DailyPlanResponse(
            id=plan_data["id"],
            user_id=plan_data["user_id"],
            plan_date=date.fromisoformat(plan_data["plan_date"]),
            tasks=tasks,
            energy_level=plan_data.get("energy_level"),
            status=plan_data["status"],
            generated_at=datetime.fromisoformat(plan_data["generated_at"].replace("Z", "+00:00")),
            created_at=datetime.fromisoformat(plan_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(plan_data["updated_at"].replace("Z", "+00:00")),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update plan: {str(e)}",
        )

