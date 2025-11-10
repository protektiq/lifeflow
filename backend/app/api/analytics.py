"""Analytics API endpoints for learning agent and metrics"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel
from app.database import supabase
from app.api.auth import get_current_user
from app.utils.monitoring import StructuredLogger
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from collections import defaultdict

router = APIRouter()
security = HTTPBearer()


class TaskTypeMetrics(BaseModel):
    """Metrics for a specific task type"""
    task_type: str  # extracted_priority value
    total_tasks: int
    completed_tasks: int
    completion_rate: float  # percentage
    average_time_minutes: Optional[float] = None  # average duration in minutes


class SourceReliabilityMetrics(BaseModel):
    """Source reliability metrics"""
    source: str
    total_tasks: int
    completed_tasks: int
    completion_rate: float  # percentage


class AnalyticsResponse(BaseModel):
    """Analytics response model"""
    task_type_metrics: List[TaskTypeMetrics]
    source_reliability: List[SourceReliabilityMetrics]
    period_start: datetime
    period_end: datetime


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


def calculate_duration_minutes(start_time: str, end_time: str) -> Optional[float]:
    """Calculate duration in minutes between two timestamps"""
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start
        return duration.total_seconds() / 60.0
    except (ValueError, TypeError, AttributeError):
        return None


@router.get("/task-type-metrics", response_model=List[TaskTypeMetrics])
async def get_task_type_metrics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user = Depends(get_authenticated_user),
):
    """
    Get historical completion rates and average time spent per task type.
    Task types are based on extracted_priority field (high, medium, low, normal).
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow().isoformat()
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        # Fetch all tasks for the user in the date range
        query = supabase.table("raw_tasks").select("*").eq("user_id", user.id)
        
        if start_date:
            query = query.gte("start_time", start_date)
        if end_date:
            query = query.lte("start_time", end_date)
        
        response = query.execute()
        tasks = response.data
        
        # Group tasks by extracted_priority (task type)
        task_type_stats = defaultdict(lambda: {
            "total": 0,
            "completed": 0,
            "durations": []
        })
        
        for task in tasks:
            task_type = task.get("extracted_priority") or "normal"
            task_type_stats[task_type]["total"] += 1
            
            if task.get("is_completed"):
                task_type_stats[task_type]["completed"] += 1
                
                # Calculate duration for completed tasks
                duration = calculate_duration_minutes(
                    task.get("start_time"),
                    task.get("end_time")
                )
                if duration is not None and duration > 0:
                    task_type_stats[task_type]["durations"].append(duration)
        
        # Build response
        metrics = []
        for task_type, stats in task_type_stats.items():
            completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            
            # Calculate average duration
            avg_duration = None
            if stats["durations"]:
                avg_duration = sum(stats["durations"]) / len(stats["durations"])
            
            metrics.append(TaskTypeMetrics(
                task_type=task_type,
                total_tasks=stats["total"],
                completed_tasks=stats["completed"],
                completion_rate=round(completion_rate, 2),
                average_time_minutes=round(avg_duration, 2) if avg_duration else None,
            ))
        
        # Sort by task type for consistent ordering
        metrics.sort(key=lambda x: x.task_type)
        
        StructuredLogger.log_event(
            "analytics_task_type_metrics_fetched",
            f"Fetched task type metrics for user {user.id}",
            user_id=user.id,
            metadata={"start_date": start_date, "end_date": end_date, "metrics_count": len(metrics)},
        )
        
        return metrics
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_task_type_metrics", "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch task type metrics: {str(e)}",
        )


@router.get("/source-reliability", response_model=List[SourceReliabilityMetrics])
async def get_source_reliability_metrics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user = Depends(get_authenticated_user),
):
    """
    Get Source Reliability metrics showing % of tasks completed from different sources
    (e.g., Email vs Calendar vs Todoist).
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow().isoformat()
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        
        # Fetch all tasks for the user in the date range
        query = supabase.table("raw_tasks").select("*").eq("user_id", user.id)
        
        if start_date:
            query = query.gte("start_time", start_date)
        if end_date:
            query = query.lte("start_time", end_date)
        
        response = query.execute()
        tasks = response.data
        
        # Group tasks by source
        source_stats = defaultdict(lambda: {
            "total": 0,
            "completed": 0
        })
        
        for task in tasks:
            source = task.get("source") or "unknown"
            source_stats[source]["total"] += 1
            
            if task.get("is_completed"):
                source_stats[source]["completed"] += 1
        
        # Build response
        metrics = []
        for source, stats in source_stats.items():
            completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
            
            metrics.append(SourceReliabilityMetrics(
                source=source,
                total_tasks=stats["total"],
                completed_tasks=stats["completed"],
                completion_rate=round(completion_rate, 2),
            ))
        
        # Sort by completion rate descending, then by source name
        metrics.sort(key=lambda x: (-x.completion_rate, x.source))
        
        StructuredLogger.log_event(
            "analytics_source_reliability_fetched",
            f"Fetched source reliability metrics for user {user.id}",
            user_id=user.id,
            metadata={"start_date": start_date, "end_date": end_date, "metrics_count": len(metrics)},
        )
        
        return metrics
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_source_reliability_metrics", "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch source reliability metrics: {str(e)}",
        )


@router.get("/comprehensive", response_model=AnalyticsResponse)
async def get_comprehensive_analytics(
    start_date: Optional[str] = Query(None, description="Start date filter (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date filter (ISO format)"),
    user = Depends(get_authenticated_user),
):
    """
    Get comprehensive analytics including both task type metrics and source reliability.
    """
    try:
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date_dt = datetime.utcnow()
            end_date = end_date_dt.isoformat()
        else:
            end_date_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        
        if not start_date:
            start_date_dt = datetime.utcnow() - timedelta(days=30)
            start_date = start_date_dt.isoformat()
        else:
            start_date_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        
        # Fetch both metrics
        task_type_metrics = await get_task_type_metrics(start_date, end_date, user)
        source_reliability = await get_source_reliability_metrics(start_date, end_date, user)
        
        return AnalyticsResponse(
            task_type_metrics=task_type_metrics,
            source_reliability=source_reliability,
            period_start=start_date_dt,
            period_end=end_date_dt,
        )
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_comprehensive_analytics", "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch comprehensive analytics: {str(e)}",
        )

