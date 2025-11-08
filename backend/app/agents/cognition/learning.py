"""Learning Agent - Analyzes user feedback patterns and adjusts scheduling"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from uuid import UUID
from app.database import supabase
from app.utils.monitoring import StructuredLogger


def analyze_snooze_patterns(user_id: str) -> Dict[str, any]:
    """
    Analyze snooze patterns for a user
    
    Args:
        user_id: User ID to analyze
        
    Returns:
        Dictionary with pattern analysis:
        - snooze_frequency_by_hour: Dict mapping hour (0-23) to snooze count
        - snooze_frequency_by_task_type: Dict mapping task patterns to snooze count
        - average_snooze_duration: Average snooze duration in minutes
        - total_snoozes: Total number of snoozes
    """
    try:
        # Get all snooze feedback for user
        response = supabase.table("task_feedback").select(
            "*, raw_tasks(title, start_time, end_time)"
        ).eq("user_id", user_id).eq("action", "snoozed").order("feedback_at", desc=False).execute()
        
        snoozes = response.data
        total_snoozes = len(snoozes)
        
        if total_snoozes == 0:
            return {
                "snooze_frequency_by_hour": {},
                "snooze_frequency_by_task_type": {},
                "average_snooze_duration": 0,
                "total_snoozes": 0,
            }
        
        # Analyze patterns
        snooze_by_hour = {}
        snooze_durations = []
        
        for snooze in snoozes:
            # Extract hour from original task time
            task_data = snooze.get("raw_tasks")
            if task_data:
                start_time_str = task_data.get("start_time")
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                        hour = start_time.hour
                        snooze_by_hour[hour] = snooze_by_hour.get(hour, 0) + 1
                    except Exception:
                        pass
            
            # Collect snooze durations
            duration = snooze.get("snooze_duration_minutes")
            if duration:
                snooze_durations.append(duration)
        
        average_duration = sum(snooze_durations) / len(snooze_durations) if snooze_durations else 0
        
        StructuredLogger.log_event(
            "learning_pattern_analysis",
            f"Analyzed {total_snoozes} snoozes for user {user_id}",
            user_id=user_id,
            metadata={
                "total_snoozes": total_snoozes,
                "average_duration": average_duration,
                "snooze_by_hour": snooze_by_hour,
            },
        )
        
        return {
            "snooze_frequency_by_hour": snooze_by_hour,
            "snooze_frequency_by_task_type": {},  # Can be extended with task categorization
            "average_snooze_duration": average_duration,
            "total_snoozes": total_snoozes,
        }
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "analyze_snooze_patterns", "user_id": user_id},
        )
        return {
            "snooze_frequency_by_hour": {},
            "snooze_frequency_by_task_type": {},
            "average_snooze_duration": 0,
            "total_snoozes": 0,
        }


def adjust_scheduling(
    user_id: str,
    task: dict,
    context: dict,
    snooze_patterns: Optional[Dict] = None
) -> Dict[str, any]:
    """
    Adjust scheduling parameters based on learning from snooze patterns
    
    Args:
        user_id: User ID
        task: Task dictionary with scheduling info
        context: Planning context (energy_level, time_constraints, etc.)
        snooze_patterns: Optional pre-computed snooze patterns
        
    Returns:
        Dictionary with adjusted parameters:
        - adjusted_start_time: Optional adjusted start time (datetime)
        - priority_adjustment: Adjustment multiplier for priority score
        - reasoning: Explanation of adjustments
    """
    try:
        # Get snooze patterns if not provided
        if snooze_patterns is None:
            snooze_patterns = analyze_snooze_patterns(user_id)
        
        adjustments = {
            "adjusted_start_time": None,
            "priority_adjustment": 1.0,
            "reasoning": [],
        }
        
        # Check if task time matches high-snooze hours
        original_start_str = task.get("start_time")
        if original_start_str:
            try:
                original_start = datetime.fromisoformat(original_start_str.replace("Z", "+00:00"))
                hour = original_start.hour
                
                snooze_by_hour = snooze_patterns.get("snooze_frequency_by_hour", {})
                total_snoozes = snooze_patterns.get("total_snoozes", 0)
                
                if total_snoozes > 0 and hour in snooze_by_hour:
                    # Calculate snooze rate for this hour
                    snooze_count = snooze_by_hour[hour]
                    snooze_rate = snooze_count / total_snoozes
                    
                    # If this hour has high snooze rate (>30%), suggest moving earlier
                    if snooze_rate > 0.3:
                        # Move task 30 minutes earlier
                        adjusted_start = original_start - timedelta(minutes=30)
                        adjustments["adjusted_start_time"] = adjusted_start
                        adjustments["reasoning"].append(
                            f"Task frequently snoozed at {hour}:00 ({snooze_rate*100:.0f}% of snoozes). "
                            f"Suggesting earlier start time."
                        )
                        
                        StructuredLogger.log_event(
                            "learning_adjustment",
                            f"Adjusted task start time due to snooze pattern",
                            user_id=user_id,
                            metadata={
                                "task_id": task.get("id"),
                                "original_hour": hour,
                                "snooze_rate": snooze_rate,
                                "adjusted_start": adjusted_start.isoformat(),
                            },
                        )
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"function": "adjust_scheduling", "task": task},
                )
        
        # Check for tasks that are rarely snoozed (high completion rate)
        # This would require querying both done and snoozed feedback
        # For now, we'll increase priority for tasks that haven't been snoozed
        
        # Priority adjustment: If task has been snoozed multiple times, slightly reduce priority
        # (user might be avoiding it)
        task_id = task.get("id")
        if task_id:
            try:
                snooze_count_response = supabase.table("task_feedback").select(
                    "id", count="exact"
                ).eq("user_id", user_id).eq("task_id", str(task_id)).eq("action", "snoozed").execute()
                
                task_snooze_count = len(snooze_count_response.data) if snooze_count_response.data else 0
                
                if task_snooze_count > 2:
                    # Task has been snoozed multiple times - reduce priority slightly
                    adjustments["priority_adjustment"] = 0.9
                    adjustments["reasoning"].append(
                        f"Task has been snoozed {task_snooze_count} times. "
                        f"Reducing priority slightly."
                    )
            except Exception:
                pass
        
        return adjustments
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "adjust_scheduling", "user_id": user_id, "task": task},
        )
        return {
            "adjusted_start_time": None,
            "priority_adjustment": 1.0,
            "reasoning": [],
        }


def get_task_completion_rate(user_id: str, task_id: str) -> float:
    """
    Get completion rate for a specific task
    
    Args:
        user_id: User ID
        task_id: Task ID
        
    Returns:
        Completion rate (0.0-1.0) based on done vs snoozed actions
    """
    try:
        # Get done count
        done_response = supabase.table("task_feedback").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("task_id", task_id).eq("action", "done").execute()
        
        done_count = len(done_response.data) if done_response.data else 0
        
        # Get snoozed count
        snoozed_response = supabase.table("task_feedback").select(
            "id", count="exact"
        ).eq("user_id", user_id).eq("task_id", task_id).eq("action", "snoozed").execute()
        
        snoozed_count = len(snoozed_response.data) if snoozed_response.data else 0
        
        total_actions = done_count + snoozed_count
        
        if total_actions == 0:
            return 1.0  # No feedback yet, assume neutral
        
        return done_count / total_actions
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "get_task_completion_rate", "user_id": user_id, "task_id": task_id},
        )
        return 1.0

