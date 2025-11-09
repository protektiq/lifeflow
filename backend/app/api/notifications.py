"""Notification API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from datetime import datetime
from app.database import supabase
from app.api.auth import get_current_user
from app.models.notification import NotificationResponse
from app.services.notification import NotificationService
from app.utils.monitoring import StructuredLogger
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


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    status_filter: Optional[str] = Query(None, description="Filter by status (pending, sent, dismissed)"),
    limit: int = Query(50, description="Maximum number of notifications to return"),
    user = Depends(get_authenticated_user),
):
    """Get notifications for the authenticated user"""
    try:
        notifications = NotificationService.get_notifications_for_user(
            user_id=user.id,
            status=status_filter,
            limit=limit,
        )
        return notifications
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_notifications", "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notifications: {str(e)}",
        )


@router.get("/pending", response_model=List[NotificationResponse])
async def get_pending_notifications(
    limit: int = Query(50, description="Maximum number of notifications to return"),
    user = Depends(get_authenticated_user),
):
    """Get pending notifications for the authenticated user"""
    try:
        notifications = NotificationService.get_notifications_for_user(
            user_id=user.id,
            status="pending",
            limit=limit,
        )
        return notifications
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_pending_notifications", "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending notifications: {str(e)}",
        )


@router.post("/{notification_id}/dismiss", status_code=status.HTTP_200_OK)
async def dismiss_notification(
    notification_id: str,
    user = Depends(get_authenticated_user),
):
    """Dismiss a notification"""
    try:
        success = NotificationService.dismiss_notification(
            notification_id=notification_id,
            user_id=user.id,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or does not belong to user",
            )
        
        return {"success": True, "message": "Notification dismissed"}
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "dismiss_notification", "notification_id": notification_id, "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss notification: {str(e)}",
        )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: str,
    user = Depends(get_authenticated_user),
):
    """Get a specific notification by ID"""
    try:
        notifications = NotificationService.get_notifications_for_user(
            user_id=user.id,
            limit=1000,  # Get more to find the specific one
        )
        
        notification = next((n for n in notifications if str(n.id) == notification_id), None)
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )
        
        return notification
    except HTTPException:
        raise
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_notification", "notification_id": notification_id, "user_id": user.id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch notification: {str(e)}",
        )

