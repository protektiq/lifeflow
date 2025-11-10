"""Calendar and Email ingestion API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
from app.agents.orchestration.workflow import run_ingestion_workflow
from app.utils.monitoring import StructuredLogger, ingestion_metrics
from app.api.auth import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()


async def get_authenticated_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get authenticated user from JWT token"""
    try:
        user = get_current_user(credentials.credentials)
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


@router.post("/calendar/sync")
async def sync_calendar(user = Depends(get_authenticated_user)):
    """Trigger calendar and email sync workflow (includes both calendar events and emails)"""
    try:
        StructuredLogger.log_event(
            "calendar_sync_requested",
            "Calendar and email sync requested",
            user_id=user.id,
        )
        
        result = await run_ingestion_workflow(user.id)
        
        if result["success"]:
            StructuredLogger.log_event(
                "calendar_sync_success",
                f"Calendar and email sync completed: {result['event_count']} items ingested",
                user_id=user.id,
                metadata=result,
            )
        else:
            StructuredLogger.log_event(
                "calendar_sync_failed",
                "Calendar and email sync failed",
                user_id=user.id,
                metadata=result,
                level="ERROR",
            )
        
        return {
            "success": result["success"],
            "status": result["status"],
            "events_ingested": result["event_count"],
            "errors": result.get("errors", []),
            "metrics": ingestion_metrics.get_metrics(),
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "sync_calendar"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calendar and email sync failed: {str(e)}",
        )


@router.post("/email/sync")
async def sync_email(user = Depends(get_authenticated_user)):
    """Trigger email sync workflow (includes both calendar events and emails)"""
    try:
        StructuredLogger.log_event(
            "email_sync_requested",
            "Email sync requested",
            user_id=user.id,
        )
        
        # Use the same workflow which now includes email ingestion
        result = await run_ingestion_workflow(user.id)
        
        if result["success"]:
            StructuredLogger.log_event(
                "email_sync_success",
                f"Email sync completed: {result['event_count']} items ingested",
                user_id=user.id,
                metadata=result,
            )
        else:
            StructuredLogger.log_event(
                "email_sync_failed",
                "Email sync failed",
                user_id=user.id,
                metadata=result,
                level="ERROR",
            )
        
        return {
            "success": result["success"],
            "status": result["status"],
            "events_ingested": result["event_count"],
            "errors": result.get("errors", []),
            "metrics": ingestion_metrics.get_metrics(),
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "sync_email"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email sync failed: {str(e)}",
        )


@router.get("/metrics")
async def get_ingestion_metrics(user = Depends(get_authenticated_user)):
    """Get ingestion metrics"""
    return {
        "metrics": ingestion_metrics.get_metrics(),
    }

