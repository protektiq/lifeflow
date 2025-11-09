"""Action Agent for sending micro-nudges when scheduled tasks are due"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from uuid import UUID
from openai import OpenAI
from app.config import settings
from app.database import supabase
from app.services.notification import NotificationService
from app.models.notification import NotificationCreate
from app.utils.monitoring import StructuredLogger
import json


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def get_user_completion_rate(user_id: str) -> float:
    """
    Get user's overall task completion rate
    
    Args:
        user_id: User ID
        
    Returns:
        Completion rate (0.0-1.0)
    """
    try:
        # Get done count
        done_response = supabase.table("task_feedback").select(
            "id", count="exact"
        ).eq("user_id", str(user_id)).eq("action", "done").execute()
        
        done_count = len(done_response.data) if done_response.data else 0
        
        # Get snoozed count
        snoozed_response = supabase.table("task_feedback").select(
            "id", count="exact"
        ).eq("user_id", str(user_id)).eq("action", "snoozed").execute()
        
        snoozed_count = len(snoozed_response.data) if snoozed_response.data else 0
        
        total_actions = done_count + snoozed_count
        
        if total_actions == 0:
            return 0.5  # Neutral if no data
        
        return done_count / total_actions
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_user_completion_rate", "user_id": str(user_id)},
        )
        return 0.5


def generate_personalized_nudge(
    user_id: str,
    task_title: str,
    task_description: Optional[str],
    is_critical: bool,
    is_urgent: bool,
    energy_level: Optional[int] = None,
    completion_rate: Optional[float] = None
) -> Optional[str]:
    """
    Generate personalized nudge message using ChatGPT
    
    Args:
        user_id: User ID
        task_title: Task title
        task_description: Optional task description
        is_critical: Whether task is critical
        is_urgent: Whether task is urgent
        energy_level: Optional user energy level (1-5)
        completion_rate: Optional user completion rate
        
    Returns:
        Personalized nudge message (max 100 characters)
    """
    try:
        # Build prompt
        system_prompt = """You are a helpful task management assistant that sends brief, motivational nudge messages.
Generate a personalized, concise nudge message (max 100 characters) that:
- Is context-aware (considers task importance, user energy)
- Is motivational but not pushy
- Includes emoji when appropriate
- Adapts tone based on task criticality
- Encourages action without being overwhelming

Return ONLY the message text, no JSON, no quotes."""
        
        # Build context
        context_parts = [f"Task: {task_title}"]
        if task_description:
            context_parts.append(f"Description: {task_description[:100]}")
        if is_critical:
            context_parts.append("CRITICAL - Must be done")
        elif is_urgent:
            context_parts.append("URGENT - Time-sensitive")
        if energy_level:
            context_parts.append(f"User energy level: {energy_level}/5")
        if completion_rate:
            completion_pct = int(completion_rate * 100)
            context_parts.append(f"User completion rate: {completion_pct}%")
        
        user_prompt = f"""Generate a personalized nudge message for this task:
{chr(10).join(context_parts)}

Message should be:
- Max 100 characters
- Motivational and encouraging
- Include emoji if appropriate
- Match the urgency level (critical/urgent/normal)
- Consider user's energy and completion patterns"""
        
        StructuredLogger.log_event(
            "chatgpt_nudge_generation_start",
            f"Generating personalized nudge for task: {task_title}",
            user_id=str(user_id),
            metadata={"task_title": task_title, "is_critical": is_critical, "is_urgent": is_urgent},
        )
        
        # Use gpt-3.5-turbo for faster response (nudges need to be timely)
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=50,  # Limit to keep messages concise
            )
        except Exception as e:
            StructuredLogger.log_event(
                "chatgpt_nudge_generation_failed",
                f"ChatGPT nudge generation failed: {str(e)}",
                user_id=str(user_id),
                metadata={"error": str(e)},
                level="WARNING"
            )
            return None
        
        # Extract message from response
        message = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        if message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
        
        # Ensure message is within character limit
        if len(message) > 100:
            message = message[:97] + "..."
        
        StructuredLogger.log_event(
            "chatgpt_nudge_generation_success",
            f"Generated personalized nudge: {message[:50]}",
            user_id=str(user_id),
            metadata={"message_length": len(message)},
        )
        
        return message
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": str(user_id),
                "function": "generate_personalized_nudge",
                "task_title": task_title
            }
        )
        return None


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
                    
                    # Get task details
                    task_title = task.get("title", "Task")
                    is_critical = task.get("is_critical", False)
                    is_urgent = task.get("is_urgent", False)
                    
                    # Get task description from raw_tasks table
                    task_description = None
                    try:
                        task_response = supabase.table("raw_tasks").select("description").eq("id", str(task_id)).execute()
                        if task_response.data and task_response.data[0].get("description"):
                            task_description = task_response.data[0]["description"]
                    except Exception:
                        pass
                    
                    # Get user context for personalization
                    energy_level = plan_data.get("energy_level")
                    completion_rate = get_user_completion_rate(str(user_id))
                    
                    # Try to generate personalized message with ChatGPT
                    message = generate_personalized_nudge(
                        user_id=str(user_id),
                        task_title=task_title,
                        task_description=task_description,
                        is_critical=is_critical,
                        is_urgent=is_urgent,
                        energy_level=energy_level,
                        completion_rate=completion_rate
                    )
                    
                    # Fallback to template-based message if ChatGPT fails
                    if not message:
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

