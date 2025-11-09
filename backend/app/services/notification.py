"""Notification service for sending micro-nudges and managing notifications"""
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from app.database import supabase
from app.models.notification import Notification, NotificationCreate, NotificationResponse
from app.services.email import EmailService
from app.utils.monitoring import StructuredLogger


class NotificationService:
    """Service for managing notifications"""
    
    @staticmethod
    def create_notification(notification: NotificationCreate) -> NotificationResponse:
        """
        Create a new notification record
        
        Args:
            notification: Notification creation data
            
        Returns:
            Created notification response
        """
        try:
            notification_data = {
                "user_id": str(notification.user_id),
                "task_id": str(notification.task_id),
                "plan_id": str(notification.plan_id) if notification.plan_id else None,
                "type": notification.type,
                "message": notification.message,
                "scheduled_at": notification.scheduled_at.isoformat(),
                "status": notification.status,
            }
            
            response = supabase.table("notifications").insert(notification_data).execute()
            
            if not response.data:
                raise ValueError("Failed to create notification")
            
            data = response.data[0]
            return NotificationResponse(
                id=UUID(data["id"]),
                user_id=UUID(data["user_id"]),
                task_id=UUID(data["task_id"]),
                plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
                type=data["type"],
                message=data["message"],
                scheduled_at=datetime.fromisoformat(data["scheduled_at"].replace("Z", "+00:00")),
                sent_at=datetime.fromisoformat(data["sent_at"].replace("Z", "+00:00")) if data.get("sent_at") else None,
                status=data["status"],
                created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
            )
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "create_notification", "user_id": str(notification.user_id)},
            )
            raise
    
    @staticmethod
    def send_notification(notification_id: UUID) -> bool:
        """
        Send notification (in-app and email) and mark as sent
        
        Args:
            notification_id: ID of the notification to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get notification details
            notification_response = supabase.table("notifications").select("*").eq("id", str(notification_id)).execute()
            
            if not notification_response.data:
                return False
            
            notification_data = notification_response.data[0]
            user_id = notification_data["user_id"]
            task_id = notification_data["task_id"]
            message = notification_data["message"]
            scheduled_at = notification_data["scheduled_at"]
            
            # Get task details for email
            task_response = supabase.table("raw_tasks").select("title, start_time, is_critical, is_urgent").eq("id", task_id).execute()
            task_data = task_response.data[0] if task_response.data else {}
            task_title = task_data.get("title", "Task")
            is_critical = task_data.get("is_critical", False)
            is_urgent = task_data.get("is_urgent", False)
            
            # Format task time
            task_time = scheduled_at
            try:
                scheduled_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                task_time = scheduled_dt.strftime("%I:%M %p")
            except Exception:
                pass
            
            # Send email notification
            try:
                user_email = EmailService.get_user_email(user_id)
                if user_email:
                    email_sent = EmailService.send_task_nudge_email(
                        user_email=user_email,
                        task_title=task_title,
                        task_time=task_time,
                        is_critical=is_critical,
                        is_urgent=is_urgent,
                    )
                    if email_sent:
                        StructuredLogger.log_event(
                            "email_nudge_sent",
                            f"Email notification sent to {user_email}",
                            user_id=user_id,
                            metadata={
                                "notification_id": str(notification_id),
                                "task_id": task_id,
                                "user_email": user_email,
                            },
                        )
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"function": "send_notification_email", "notification_id": str(notification_id)},
                )
                # Continue even if email fails - in-app notification still works
            
            # Mark notification as sent in database
            now = datetime.utcnow()
            response = supabase.table("notifications").update({
                "status": "sent",
                "sent_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }).eq("id", str(notification_id)).execute()
            
            if response.data:
                StructuredLogger.log_event(
                    "nudge_sent",
                    f"Notification {notification_id} sent",
                    user_id=user_id,
                    metadata={
                        "notification_id": str(notification_id),
                        "task_id": task_id,
                        "type": notification_data["type"],
                    },
                )
                return True
            return False
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "send_notification", "notification_id": str(notification_id)},
            )
            return False
    
    @staticmethod
    def get_pending_notifications(user_id: Optional[UUID] = None, limit: int = 100) -> List[NotificationResponse]:
        """
        Get pending notifications
        
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of notifications to return
            
        Returns:
            List of pending notifications
        """
        try:
            query = supabase.table("notifications").select("*").eq("status", "pending").order("scheduled_at", desc=False).limit(limit)
            
            if user_id:
                query = query.eq("user_id", str(user_id))
            
            response = query.execute()
            
            notifications = []
            for data in response.data:
                notifications.append(NotificationResponse(
                    id=UUID(data["id"]),
                    user_id=UUID(data["user_id"]),
                    task_id=UUID(data["task_id"]),
                    plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
                    type=data["type"],
                    message=data["message"],
                    scheduled_at=datetime.fromisoformat(data["scheduled_at"].replace("Z", "+00:00")),
                    sent_at=datetime.fromisoformat(data["sent_at"].replace("Z", "+00:00")) if data.get("sent_at") else None,
                    status=data["status"],
                    created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
                ))
            
            return notifications
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "get_pending_notifications", "user_id": str(user_id) if user_id else None},
            )
            return []
    
    @staticmethod
    def get_notifications_for_user(user_id: UUID, status: Optional[str] = None, limit: int = 50) -> List[NotificationResponse]:
        """
        Get notifications for a specific user
        
        Args:
            user_id: User ID
            status: Optional status filter (pending, sent, dismissed)
            limit: Maximum number of notifications to return
            
        Returns:
            List of notifications
        """
        try:
            query = supabase.table("notifications").select("*").eq("user_id", str(user_id)).order("created_at", desc=True).limit(limit)
            
            if status:
                query = query.eq("status", status)
            
            response = query.execute()
            
            notifications = []
            for data in response.data:
                notifications.append(NotificationResponse(
                    id=UUID(data["id"]),
                    user_id=UUID(data["user_id"]),
                    task_id=UUID(data["task_id"]),
                    plan_id=UUID(data["plan_id"]) if data.get("plan_id") else None,
                    type=data["type"],
                    message=data["message"],
                    scheduled_at=datetime.fromisoformat(data["scheduled_at"].replace("Z", "+00:00")),
                    sent_at=datetime.fromisoformat(data["sent_at"].replace("Z", "+00:00")) if data.get("sent_at") else None,
                    status=data["status"],
                    created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")) if data.get("updated_at") else None,
                ))
            
            return notifications
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "get_notifications_for_user", "user_id": str(user_id)},
            )
            return []
    
    @staticmethod
    def dismiss_notification(notification_id: UUID, user_id: UUID) -> bool:
        """
        Dismiss a notification
        
        Args:
            notification_id: ID of the notification to dismiss
            user_id: User ID for validation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Verify notification belongs to user
            check = supabase.table("notifications").select("id").eq("id", str(notification_id)).eq("user_id", str(user_id)).execute()
            
            if not check.data:
                return False
            
            now = datetime.utcnow()
            response = supabase.table("notifications").update({
                "status": "dismissed",
                "updated_at": now.isoformat(),
            }).eq("id", str(notification_id)).execute()
            
            return bool(response.data)
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "dismiss_notification", "notification_id": str(notification_id), "user_id": str(user_id)},
            )
            return False
    
    @staticmethod
    def has_notification_for_task(task_id: UUID, status: Optional[str] = None) -> bool:
        """
        Check if a notification already exists for a task
        
        Args:
            task_id: Task ID to check
            status: Optional status filter (pending, sent, dismissed)
            
        Returns:
            True if notification exists, False otherwise
        """
        try:
            query = supabase.table("notifications").select("id").eq("task_id", str(task_id))
            
            if status:
                query = query.eq("status", status)
            
            response = query.execute()
            return len(response.data) > 0
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "has_notification_for_task", "task_id": str(task_id)},
            )
            return False

