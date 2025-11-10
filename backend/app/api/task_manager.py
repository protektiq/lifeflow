"""Task Manager Sync API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from app.api.auth import get_current_user
from app.services.task_sync_service import task_sync_service, TaskManagerIntegrationError
from app.utils.monitoring import StructuredLogger

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


class ConflictResolutionRequest(BaseModel):
    """Request model for conflict resolution"""
    resolution: str  # "local" or "external"
    task_id: str


@router.post("/todoist/sync")
async def sync_todoist(user = Depends(get_authenticated_user)):
    """Trigger full bidirectional sync with Todoist"""
    try:
        StructuredLogger.log_event(
            "todoist_sync_requested",
            "Todoist sync requested",
            user_id=user.id,
        )
        
        result = await task_sync_service.sync_tasks_bidirectional(user.id, "todoist")
        
        if result["success"]:
            StructuredLogger.log_event(
                "todoist_sync_success",
                f"Todoist sync completed successfully",
                user_id=user.id,
                metadata=result,
            )
        else:
            StructuredLogger.log_event(
                "todoist_sync_failed",
                "Todoist sync failed",
                user_id=user.id,
                metadata=result,
                level="ERROR",
            )
        
        return {
            "success": result["success"],
            "inbound": result.get("inbound", {}),
            "outbound": result.get("outbound", {}),
        }
    except TaskManagerIntegrationError as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "sync_todoist"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Todoist sync failed: {str(e)}",
        )
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "sync_todoist"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Todoist sync failed: {str(e)}",
        )


@router.get("/todoist/status")
async def get_todoist_status(user = Depends(get_authenticated_user)):
    """Get Todoist sync status and last sync time"""
    try:
        from app.database import supabase
        
        # Check if user has Todoist connected
        token_response = supabase.table("oauth_tokens").select("*").eq(
            "user_id", user.id
        ).eq("provider", "todoist").execute()
        
        is_connected = len(token_response.data) > 0
        
        if not is_connected:
            return {
                "connected": False,
                "last_sync": None,
                "sync_status": "not_connected",
            }
        
        # Get last sync time from tasks
        tasks_response = supabase.table("raw_tasks").select("last_synced_at").eq(
            "user_id", user.id
        ).eq("source", "todoist").order("last_synced_at", desc=True).limit(1).execute()
        
        last_sync = None
        if tasks_response.data and tasks_response.data[0].get("last_synced_at"):
            last_sync = tasks_response.data[0]["last_synced_at"]
        
        # Get sync status counts
        status_response = supabase.table("raw_tasks").select("sync_status").eq(
            "user_id", user.id
        ).eq("source", "todoist").execute()
        
        status_counts = {}
        conflicts = []
        errors = []
        
        for task in status_response.data:
            sync_status = task.get("sync_status", "pending")
            status_counts[sync_status] = status_counts.get(sync_status, 0) + 1
            
            if sync_status == "conflict":
                conflicts.append(task)
            elif sync_status == "error":
                errors.append(task)
        
        return {
            "connected": True,
            "last_sync": last_sync,
            "sync_status": "synced" if status_counts.get("synced", 0) > 0 else "pending",
            "status_counts": status_counts,
            "conflicts_count": len(conflicts),
            "errors_count": len(errors),
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "get_todoist_status"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Todoist status: {str(e)}",
        )


@router.post("/todoist/resolve-conflict")
async def resolve_todoist_conflict(
    request: ConflictResolutionRequest,
    user = Depends(get_authenticated_user)
):
    """Resolve a sync conflict"""
    try:
        if request.resolution not in ["local", "external"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resolution must be 'local' or 'external'",
            )
        
        result = await task_sync_service.resolve_conflict(
            user.id,
            request.task_id,
            request.resolution,
            "todoist"
        )
        
        StructuredLogger.log_event(
            "conflict_resolved",
            f"Resolved conflict for task {request.task_id}",
            user_id=user.id,
            metadata={"task_id": request.task_id, "resolution": request.resolution},
        )
        
        return result
    except TaskManagerIntegrationError as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "resolve_todoist_conflict"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}",
        )
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user.id, "endpoint": "resolve_todoist_conflict"})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve conflict: {str(e)}",
        )

