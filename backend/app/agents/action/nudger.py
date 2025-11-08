"""Action Agent for sending micro-nudges when scheduled tasks are due"""
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from uuid import UUID
from app.database import supabase
from app.services.notification import NotificationService
from app.models.notification import NotificationCreate
from app.utils.monitoring import StructuredLogger


async def check_and_send_nudges() -> Dict[str, int]:
    """
    Check for tasks due to start and send micro-nudges
    
    This function:
    1. Queries daily_plans for active plans
    2. Extracts tasks with predicted_start within next 5 minutes
    3. Filters out tasks that already have pending/sent notifications
    4. Creates notification records for tasks due to start
    5. Sends single, clear, high-priority micro-nudge per task
    
    Returns:
        Dictionary with counts: {'checked': int, 'nudges_sent': int, 'skipped': int}
    """
    try:
        now = datetime.now(timezone.utc)
        # Check for tasks starting in the next 5 minutes
        window_start = now
        window_end = now + timedelta(minutes=5)
        
        StructuredLogger.log_event(
            "nudger_check_start",
            f"Checking for tasks due between {window_start.isoformat()} and {window_end.isoformat()}",
            metadata={
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            },
        )
        
        # Get all active daily plans
        plans_response = supabase.table("daily_plans").select("*").eq(
            "status", "active"
        ).execute()
        
        checked_count = 0
        nudges_sent = 0
        skipped_count = 0
        
        for plan_data in plans_response.data:
            user_id = UUID(plan_data["user_id"])
            plan_id = UUID(plan_data["id"])
            plan_date = plan_data["plan_date"]
            tasks = plan_data.get("tasks", [])
            
            if not tasks:
                continue
            
            # Process each task in the plan
            for task in tasks:
                checked_count += 1
                
                try:
                    task_id = UUID(task.get("task_id"))
                    predicted_start_str = task.get("predicted_start")
                    
                    if not predicted_start_str:
                        continue
                    
                    # Parse predicted_start datetime
                    if isinstance(predicted_start_str, str):
                        # Handle ISO format strings
                        predicted_start = datetime.fromisoformat(
                            predicted_start_str.replace("Z", "+00:00")
                        )
                    else:
                        continue
                    
                    # Ensure timezone-aware
                    if predicted_start.tzinfo is None:
                        predicted_start = predicted_start.replace(tzinfo=timezone.utc)
                    
                    # Check if task is within the time window
                    if predicted_start < window_start or predicted_start > window_end:
                        continue
                    
                    # Check if notification already exists for this task
                    if NotificationService.has_notification_for_task(task_id, status="pending"):
                        skipped_count += 1
                        StructuredLogger.log_event(
                            "nudger_skip_existing",
                            f"Skipping task {task_id} - notification already exists",
                            user_id=str(user_id),
                            metadata={"task_id": str(task_id)},
                        )
                        continue
                    
                    # Check if notification was already sent
                    if NotificationService.has_notification_for_task(task_id, status="sent"):
                        skipped_count += 1
                        continue
                    
                    # Create micro-nudge message
                    task_title = task.get("title", "Task")
                    is_critical = task.get("is_critical", False)
                    is_urgent = task.get("is_urgent", False)
                    
                    # Build clear, high-priority message
                    if is_critical:
                        message = f"🔴 CRITICAL: {task_title} is starting now"
                    elif is_urgent:
                        message = f"⚠️ URGENT: {task_title} is starting now"
                    else:
                        message = f"📋 {task_title} is starting now"
                    
                    # Create notification
                    notification = NotificationCreate(
                        user_id=user_id,
                        task_id=task_id,
                        plan_id=plan_id,
                        type="nudge",
                        message=message,
                        scheduled_at=predicted_start,
                        status="pending",
                    )
                    
                    # Create and send notification
                    created_notification = NotificationService.create_notification(notification)
                    NotificationService.send_notification(created_notification.id)
                    
                    nudges_sent += 1
                    
                    StructuredLogger.log_event(
                        "nudger_nudge_sent",
                        f"Sent nudge for task {task_title}",
                        user_id=str(user_id),
                        metadata={
                            "task_id": str(task_id),
                            "plan_id": str(plan_id),
                            "predicted_start": predicted_start.isoformat(),
                            "is_critical": is_critical,
                            "is_urgent": is_urgent,
                        },
                    )
                    
                except Exception as e:
                    StructuredLogger.log_error(
                        e,
                        context={
                            "function": "check_and_send_nudges",
                            "user_id": str(user_id),
                            "task": task,
                        },
                    )
                    skipped_count += 1
                    continue
        
        result = {
            "checked": checked_count,
            "nudges_sent": nudges_sent,
            "skipped": skipped_count,
        }
        
        StructuredLogger.log_event(
            "nudger_check_complete",
            f"Checked {checked_count} tasks, sent {nudges_sent} nudges, skipped {skipped_count}",
            metadata=result,
        )
        
        return result
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "check_and_send_nudges"},
        )
        return {
            "checked": 0,
            "nudges_sent": 0,
            "skipped": 0,
            "error": str(e),
        }

