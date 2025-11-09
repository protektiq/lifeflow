"""Learning Agent - Analyzes user feedback patterns and adjusts scheduling"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from uuid import UUID
from openai import OpenAI
from app.config import settings
from app.database import supabase
from app.utils.monitoring import StructuredLogger
import json


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


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


def analyze_patterns_with_chatgpt(
    user_id: str,
    snooze_patterns: Dict,
    task_history: Optional[List[Dict]] = None
) -> Optional[Dict]:
    """
    Use ChatGPT to analyze user patterns and provide insights
    
    Args:
        user_id: User ID
        snooze_patterns: Dictionary with snooze pattern data
        task_history: Optional list of recent tasks for context
        
    Returns:
        Dictionary with ChatGPT insights or None if analysis fails:
        - patterns: List of identified patterns
        - recommendations: List of personalized recommendations
        - reasoning: Explanation of patterns
        - confidence: Confidence score (0.0-1.0)
    """
    try:
        total_snoozes = snooze_patterns.get("total_snoozes", 0)
        
        if total_snoozes < 3:
            # Not enough data for meaningful analysis
            return None
        
        snooze_by_hour = snooze_patterns.get("snooze_frequency_by_hour", {})
        average_duration = snooze_patterns.get("average_snooze_duration", 0)
        
        # Build prompt with pattern data
        system_prompt = """You are an expert at analyzing user behavior patterns from task management data.
Analyze the snooze patterns and provide insights about:
1. When the user tends to snooze tasks (time patterns)
2. Why they might be snoozing (energy levels, task complexity, etc.)
3. Personalized recommendations for better scheduling

Return a JSON object with your analysis."""
        
        # Format snooze data for prompt
        hour_patterns = []
        for hour, count in sorted(snooze_by_hour.items(), key=lambda x: x[1], reverse=True)[:5]:
            hour_patterns.append(f"{hour}:00 - {count} snoozes")
        
        user_prompt = f"""User has {total_snoozes} total snoozes with average duration of {average_duration:.0f} minutes.

Top snooze hours:
{chr(10).join(hour_patterns) if hour_patterns else 'No clear patterns'}

Analyze these patterns and provide:
- patterns: List of 2-3 key patterns identified (e.g., "User avoids complex tasks in afternoon")
- recommendations: List of 2-3 personalized recommendations
- reasoning: Brief explanation of why these patterns exist (max 100 words)
- confidence: Confidence score 0.0-1.0 based on data quality

Return JSON with these fields."""
        
        StructuredLogger.log_event(
            "chatgpt_learning_analysis_start",
            f"Starting ChatGPT pattern analysis for user {user_id}",
            user_id=user_id,
            metadata={"total_snoozes": total_snoozes},
        )
        
        # Try gpt-4o first, fallback to gpt-3.5-turbo
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            StructuredLogger.log_event(
                "chatgpt_learning_fallback",
                f"gpt-4o failed, trying gpt-3.5-turbo: {str(e)}",
                user_id=user_id,
                metadata={"error": str(e)},
                level="WARNING"
            )
            try:
                response = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.5,
                    response_format={"type": "json_object"}
                )
            except Exception as e2:
                StructuredLogger.log_event(
                    "chatgpt_learning_failed",
                    f"ChatGPT pattern analysis failed: {str(e2)}",
                    user_id=user_id,
                    metadata={"error": str(e2)},
                    level="WARNING"
                )
                return None
        
        # Parse response
        content = response.choices[0].message.content
        analysis_result = json.loads(content)
        
        StructuredLogger.log_event(
            "chatgpt_learning_analysis_success",
            f"ChatGPT pattern analysis completed for user {user_id}",
            user_id=user_id,
            metadata={
                "patterns_count": len(analysis_result.get("patterns", [])),
                "confidence": analysis_result.get("confidence", 0.0),
            },
        )
        
        return analysis_result
        
    except json.JSONDecodeError as e:
        StructuredLogger.log_event(
            "chatgpt_learning_json_error",
            f"Failed to parse ChatGPT JSON response: {str(e)}",
            user_id=user_id,
            metadata={"error": str(e)},
            level="WARNING"
        )
        return None
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": user_id,
                "function": "analyze_patterns_with_chatgpt"
            }
        )
        return None


def generate_learning_explanation(
    user_id: str,
    adjustments: Dict,
    chatgpt_insights: Optional[Dict] = None
) -> str:
    """
    Generate user-facing explanation for scheduling adjustments
    
    Args:
        user_id: User ID
        adjustments: Dictionary with adjustment data
        chatgpt_insights: Optional ChatGPT insights
        
    Returns:
        Human-readable explanation string
    """
    try:
        reasoning_parts = adjustments.get("reasoning", [])
        
        if chatgpt_insights and chatgpt_insights.get("reasoning"):
            # Use ChatGPT reasoning if available
            chatgpt_reasoning = chatgpt_insights.get("reasoning", "")
            if chatgpt_reasoning:
                return chatgpt_reasoning
        
        # Fallback to rule-based reasoning
        if reasoning_parts:
            return " ".join(reasoning_parts)
        
        return "Schedule adjusted based on your task completion patterns."
        
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": user_id,
                "function": "generate_learning_explanation"
            }
        )
        return "Schedule adjusted based on your patterns."


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
        - chatgpt_insights: Optional ChatGPT analysis insights
    """
    try:
        # Get snooze patterns if not provided
        if snooze_patterns is None:
            snooze_patterns = analyze_snooze_patterns(user_id)
        
        adjustments = {
            "adjusted_start_time": None,
            "priority_adjustment": 1.0,
            "reasoning": [],
            "chatgpt_insights": None,
        }
        
        # Try ChatGPT analysis for better pattern understanding
        chatgpt_insights = None
        try:
            chatgpt_insights = analyze_patterns_with_chatgpt(user_id, snooze_patterns)
            if chatgpt_insights:
                adjustments["chatgpt_insights"] = chatgpt_insights
                # Incorporate ChatGPT recommendations into reasoning
                recommendations = chatgpt_insights.get("recommendations", [])
                if recommendations:
                    adjustments["reasoning"].extend(recommendations[:2])  # Add top 2 recommendations
        except Exception as e:
            StructuredLogger.log_event(
                "learning_chatgpt_analysis_error",
                f"ChatGPT analysis failed, using rule-based: {str(e)}",
                user_id=user_id,
                metadata={"error": str(e)},
                level="WARNING"
            )
            # Continue with rule-based logic
        
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

