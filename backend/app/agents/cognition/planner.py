"""LLM Planner for daily adaptive scheduling"""
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta, timezone
from uuid import UUID
from openai import OpenAI
from app.config import settings
from app.models.plan import DailyPlan, DailyPlanTask, PlanningContext
from app.agents.cognition.reinforcement import score_task_fit, _get_priority_score
from app.agents.cognition.learning import analyze_snooze_patterns, adjust_scheduling
from app.utils.monitoring import StructuredLogger
import json
import re


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


def generate_daily_plan(context: PlanningContext) -> DailyPlan:
    """
    Generate daily plan using LLM with reinforcement scoring
    
    Args:
        context: Planning context with raw tasks, energy level, etc.
    
    Returns:
        DailyPlan with scheduled tasks
    """
    # Get user_id from first task
    user_id = None
    if context.raw_tasks:
        user_id_str = context.raw_tasks[0]["user_id"]
        user_id = str(UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str)
    
    # Analyze snooze patterns for learning
    snooze_patterns = None
    if user_id:
        try:
            snooze_patterns = analyze_snooze_patterns(user_id)
            StructuredLogger.log_event(
                "planner_learning_applied",
                f"Applied learning patterns for user {user_id}",
                user_id=user_id,
                metadata={
                    "total_snoozes": snooze_patterns.get("total_snoozes", 0),
                },
            )
        except Exception as e:
            StructuredLogger.log_error(
                e,
                context={"function": "generate_daily_plan", "user_id": user_id},
            )
            # Continue without learning adjustments if analysis fails
    
    # Handle empty task list
    if not context.raw_tasks:
        StructuredLogger.log_event(
            "planner_no_tasks",
            f"No tasks to plan for {context.plan_date.isoformat()}",
            user_id=user_id or "unknown",
            metadata={"plan_date": context.plan_date.isoformat()},
        )
        # Return empty plan
        return DailyPlan(
            user_id=UUID(user_id) if user_id else None,
            plan_date=context.plan_date,
            tasks=[],
            energy_level=context.energy_level,
            status="active"
        )
    
    # Score all tasks using reinforcement agent and apply learning adjustments
    scored_tasks = []
    for task in context.raw_tasks:
        # Get base fit score
        base_score = score_task_fit(task, context.energy_level, context.time_constraints)
        
        # Apply learning adjustments
        learning_adjustments = None
        if user_id:
            try:
                learning_adjustments = adjust_scheduling(
                    user_id,
                    task,
                    {
                        "energy_level": context.energy_level,
                        "time_constraints": context.time_constraints,
                    },
                    snooze_patterns,
                )
                
                # Apply priority adjustment to fit score
                adjusted_score = base_score * learning_adjustments.get("priority_adjustment", 1.0)
                
                # Apply adjusted start time if provided
                if learning_adjustments.get("adjusted_start_time"):
                    task["start_time"] = learning_adjustments["adjusted_start_time"].isoformat()
                    # Also adjust end time to maintain duration
                    if task.get("end_time"):
                        original_start = datetime.fromisoformat(task.get("original_start_time", task["start_time"]).replace("Z", "+00:00"))
                        original_end = datetime.fromisoformat(task["end_time"].replace("Z", "+00:00"))
                        duration = original_end - original_start
                        new_end = learning_adjustments["adjusted_start_time"] + duration
                        task["end_time"] = new_end.isoformat()
                
                base_score = adjusted_score
                
                # Log learning adjustments
                if learning_adjustments.get("reasoning"):
                    StructuredLogger.log_event(
                        "planner_learning_adjustment",
                        f"Applied learning adjustment to task",
                        user_id=user_id,
                        metadata={
                            "task_id": str(task.get("id")),
                            "adjustments": learning_adjustments,
                        },
                    )
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"function": "generate_daily_plan", "task": task},
                )
                # Continue with base score if learning fails
        
        scored_tasks.append({
            **task,
            "fit_score": base_score,
            "learning_adjustments": learning_adjustments,
        })
    
    # Sort by score (highest first), but critical/urgent first
    scored_tasks.sort(key=lambda t: (
        not t.get("is_critical", False),  # Critical first
        not t.get("is_urgent", False),    # Urgent second
        -t["fit_score"]  # Then by fit score descending
    ))
    
    # Build LLM prompt
    system_prompt = """You are an intelligent daily planning assistant that creates adaptive schedules based on:
1. Task priority and importance
2. User's energy level (1-5 scale, where 1 is low energy and 5 is high energy)
3. Time constraints from calendar events
4. Critical/urgent flags that override normal scheduling

Your goal is to create a realistic, executable daily plan that:
- INCLUDES ALL tasks provided (do not filter or exclude any tasks)
- Places critical tasks early in the day regardless of energy level
- Matches task complexity to user's energy level when possible
- Respects hard time constraints (start_time, end_time from calendar)
- Provides realistic time estimates for each task
- Accounts for breaks and transitions between tasks
- Tasks with "normal" priority should still be included in the plan

IMPORTANT: 
- All predicted_start and predicted_end times MUST be on the plan_date specified. 
- If a task's original time is on a different date, adjust it to the plan_date while preserving the time of day.
- Use ISO format with timezone (e.g., "2025-11-08T14:30:00Z" for November 8th at 2:30 PM UTC).
- For ALL-DAY tasks (marked with 📅): Set predicted_start to plan_date 00:00:00 UTC and predicted_end to plan_date 23:59:59 UTC, or use the original start/end times if they span the full day.

Return a JSON object with this exact structure:
{
  "tasks": [
    {
      "task_id": "uuid-string",
      "predicted_start": "ISO datetime string (must be on plan_date)",
      "predicted_end": "ISO datetime string (must be on plan_date)",
      "priority_score": 0.0-1.0,
      "title": "task title",
      "is_critical": boolean,
      "is_urgent": boolean,
      "action_plan": ["step 1", "step 2", "step 3"]  // List of 3-7 actionable steps to complete this task
    }
  ]
}

IMPORTANT for action_plan:
- Break down each task into concrete, actionable steps
- Steps should be specific and executable (e.g., "Draft outline of proposal sections" not "Work on proposal")
- Include 3-7 steps depending on task complexity
- Steps should be ordered logically (first step first)
- For simple tasks, fewer steps are fine (e.g., "Review proposal" might have 2-3 steps)
- For complex tasks, break them down more (e.g., "Build proposal deck" should have 5-7 steps)

Ensure predicted_start and predicted_end are on the plan_date and respect the original task's time constraints.
Tasks should be ordered chronologically by predicted_start."""

    # Build user prompt with context
    user_prompt = _build_planning_prompt(context, scored_tasks)
    
    # Log what we're sending to the LLM
    StructuredLogger.log_event(
        "planner_input",
        f"Planning for {len(scored_tasks)} tasks on {context.plan_date.isoformat()}",
        user_id=str(context.raw_tasks[0]["user_id"]) if context.raw_tasks else "unknown",
        metadata={
            "plan_date": context.plan_date.isoformat(),
            "energy_level": context.energy_level,
            "tasks": [
                {
                    "title": t.get("title"),
                    "start_time": str(t.get("start_time")),
                    "end_time": str(t.get("end_time")),
                    "is_critical": t.get("is_critical", False),
                    "is_urgent": t.get("is_urgent", False),
                }
                for t in scored_tasks[:5]  # First 5 tasks
            ]
        }
    )
    
    # Call OpenAI
    # Use models that support JSON mode: gpt-4o, gpt-4-turbo, or gpt-3.5-turbo
    # Try gpt-4o first (newest, supports JSON mode), fallback to gpt-3.5-turbo
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        # Fallback to gpt-3.5-turbo which definitely supports JSON mode
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
        except Exception:
            # Last resort: use gpt-4 without JSON mode and parse JSON from text
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON, no other text."},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            # Extract JSON from response (might be wrapped in markdown code blocks)
            content = response.choices[0].message.content
            # Try to extract JSON from markdown code blocks if present
            json_match = re.search(r'```(?:json)?\s*(\{.*\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            response.choices[0].message.content = content
    
    # Parse response
    plan_data = json.loads(response.choices[0].message.content)
    
    # Log what the LLM returned
    StructuredLogger.log_event(
        "planner_output",
        f"LLM generated plan with {len(plan_data.get('tasks', []))} tasks",
        user_id=str(context.raw_tasks[0]["user_id"]) if context.raw_tasks else "unknown",
        metadata={
            "plan_date": context.plan_date.isoformat(),
            "tasks": [
                {
                    "title": t.get("title"),
                    "predicted_start": t.get("predicted_start"),
                    "predicted_end": t.get("predicted_end"),
                }
                for t in plan_data.get("tasks", [])[:5]  # First 5 tasks
            ]
        }
    )
    
    # Convert to DailyPlan model
    plan_tasks = []
    from datetime import timezone, timedelta, time as dt_time
    
    # Create a map of task_id to task info for quick lookup
    task_map = {str(task.get("id")): task for task in context.raw_tasks}
    task_all_day_map = {task.get("id"): task.get("is_all_day", False) for task in context.raw_tasks}
    
    # Track which tasks were included in the plan
    included_task_ids = set()
    
    for task_data in plan_data.get("tasks", []):
        task_id = task_data.get("task_id")
        is_all_day = task_all_day_map.get(task_id, False)
        
        original_predicted_start = datetime.fromisoformat(task_data["predicted_start"].replace("Z", "+00:00"))
        original_predicted_end = datetime.fromisoformat(task_data["predicted_end"].replace("Z", "+00:00"))
        
        # For all-day tasks, ensure times span the full day
        if is_all_day:
            # Set to start and end of plan_date in UTC
            predicted_start = datetime.combine(context.plan_date, dt_time.min).replace(tzinfo=timezone.utc)
            predicted_end = datetime.combine(context.plan_date, dt_time.max).replace(tzinfo=timezone.utc)
            
            # Get action plan and description from LLM response or original task
            task_id_str = str(task_id)
            action_plan = task_data.get("action_plan", [])
            description = task_map.get(task_id_str, {}).get("description")
            
            # Use the adjusted times
            plan_tasks.append(DailyPlanTask(
                task_id=task_id,
                predicted_start=predicted_start,
                predicted_end=predicted_end,
                priority_score=float(task_data.get("priority_score", 0.5)),
                title=task_data.get("title", ""),
                is_critical=task_data.get("is_critical", False),
                is_urgent=task_data.get("is_urgent", False),
                action_plan=action_plan if action_plan else None,
                description=description
            ))
            included_task_ids.add(task_id_str)
            continue
        
        # Calculate duration before any adjustments
        duration = original_predicted_end - original_predicted_start
        
        # Validate that predicted times are on the plan_date
        # Convert to UTC date for comparison to handle timezone issues
        if original_predicted_start.tzinfo:
            # Convert to UTC and get date
            predicted_start_utc = original_predicted_start.astimezone(timezone.utc)
            predicted_start_date = predicted_start_utc.date()
            # Get time in UTC
            time_part_utc = predicted_start_utc.time()
        else:
            # Assume UTC if no timezone info
            predicted_start_date = original_predicted_start.date()
            time_part_utc = original_predicted_start.time()
        
        # Adjust if date doesn't match plan_date
        if predicted_start_date != context.plan_date:
            # Adjust predicted_start to be on plan_date while preserving UTC time of day
            predicted_start = datetime.combine(context.plan_date, time_part_utc).replace(tzinfo=timezone.utc)
            # Adjust predicted_end by same duration
            predicted_end = predicted_start + duration
            
            StructuredLogger.log_event(
                "planner_date_adjustment",
                f"Adjusted predicted_start from {task_data['predicted_start']} to {predicted_start.isoformat()}",
                user_id=str(context.raw_tasks[0]["user_id"]) if context.raw_tasks else "unknown",
                metadata={
                    "original_start": task_data["predicted_start"],
                    "adjusted_start": predicted_start.isoformat(),
                    "plan_date": context.plan_date.isoformat(),
                    "predicted_start_date": predicted_start_date.isoformat(),
                },
                level="WARNING"
            )
        else:
            predicted_start = original_predicted_start
            predicted_end = original_predicted_end
        
        # Get action plan and description from LLM response or original task
        task_id_str = str(task_data["task_id"])
        action_plan = task_data.get("action_plan", [])
        description = task_map.get(task_id_str, {}).get("description")
        original_task = task_map.get(task_id_str, {})
        
        # If LLM didn't provide action plan, generate one
        if not action_plan or len(action_plan) == 0:
            user_id_for_logging = str(context.raw_tasks[0]["user_id"]) if context.raw_tasks else None
            action_plan = _generate_action_plan_for_task(original_task, user_id_for_logging)
        
        plan_tasks.append(DailyPlanTask(
            task_id=task_data["task_id"],
            predicted_start=predicted_start,
            predicted_end=predicted_end,
            priority_score=float(task_data.get("priority_score", 0.5)),
            title=task_data.get("title", ""),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            action_plan=action_plan if action_plan else None,
            description=description
        ))
        
        included_task_ids.add(task_id_str)
    
    # Validate that all tasks were included
    missing_tasks = []
    for task_id, task in task_map.items():
        if task_id not in included_task_ids:
            missing_tasks.append({
                "id": task_id,
                "title": task.get("title", "Unknown"),
                "priority": task.get("extracted_priority", "normal"),
            })
    
    if missing_tasks:
        StructuredLogger.log_event(
            "planner_missing_tasks",
            f"LLM excluded {len(missing_tasks)} tasks from plan",
            user_id=str(context.raw_tasks[0]["user_id"]) if context.raw_tasks else "unknown",
            metadata={
                "plan_date": context.plan_date.isoformat(),
                "missing_tasks": missing_tasks,
                "total_tasks": len(context.raw_tasks),
                "included_tasks": len(included_task_ids),
            },
            level="WARNING"
        )
        
        # Add missing tasks with default scheduling (preserve original times)
        for missing_task_info in missing_tasks:
            task_id = missing_task_info["id"]
            original_task = task_map[task_id]
            
            # Use original start/end times, adjusted to plan_date if needed
            original_start = datetime.fromisoformat(original_task["start_time"].replace("Z", "+00:00"))
            original_end = datetime.fromisoformat(original_task["end_time"].replace("Z", "+00:00"))
            
            # Adjust to plan_date if needed
            if original_start.date() != context.plan_date:
                # Preserve time of day, move to plan_date
                time_part = original_start.time()
                predicted_start = datetime.combine(context.plan_date, time_part).replace(tzinfo=timezone.utc)
                duration = original_end - original_start
                predicted_end = predicted_start + duration
            else:
                predicted_start = original_start
                predicted_end = original_end
            
            # Calculate priority score for missing task
            priority_score = _get_priority_score(original_task.get("extracted_priority"))
            
            # Generate action plan for missing task (LLM didn't include it, so generate one)
            action_plan = _generate_action_plan_for_task(original_task, user_id)
            
            plan_tasks.append(DailyPlanTask(
                task_id=task_id,
                predicted_start=predicted_start,
                predicted_end=predicted_end,
                priority_score=priority_score,
                title=original_task.get("title", "Unknown"),
                is_critical=original_task.get("is_critical", False),
                is_urgent=original_task.get("is_urgent", False),
                action_plan=action_plan,
                description=original_task.get("description")
            ))
    
    # Get user_id from first task, convert to UUID if string
    user_id = None
    if context.raw_tasks:
        user_id_str = context.raw_tasks[0]["user_id"]
        user_id = UUID(user_id_str) if isinstance(user_id_str, str) else user_id_str
    
    return DailyPlan(
        user_id=user_id,
        plan_date=context.plan_date,
        tasks=plan_tasks,
        energy_level=context.energy_level,
        status="active"
    )


def _build_planning_prompt(context: PlanningContext, scored_tasks: List[Dict]) -> str:
    """Build the user prompt for LLM planning"""
    prompt_parts = [
        f"User Energy Level: {context.energy_level}/5",
        f"Plan Date: {context.plan_date.isoformat()}",
        "",
        "Tasks to schedule:"
    ]
    
    for i, task in enumerate(scored_tasks, 1):
        is_all_day = task.get("is_all_day", False)
        task_info = [
            f"{i}. {task.get('title', 'Untitled')}",
            f"   Task ID: {task.get('id', 'unknown')}",
        ]
        
        if is_all_day:
            task_info.append("   📅 ALL-DAY TASK - Do NOT assign specific times, just include it in the plan")
        else:
            task_info.append(f"   Original Time: {task.get('start_time')} to {task.get('end_time')}")
        
        task_info.extend([
            f"   Priority: {task.get('extracted_priority', 'normal')}",
            f"   Fit Score: {task.get('fit_score', 0):.2f}",
        ])
        
        if task.get("description"):
            task_info.append(f"   Description: {task.get('description')[:500]}")  # Increased to 500 for better context
        
        # Include context that might help with breaking down the task
        if task.get("attendees"):
            task_info.append(f"   Context: This task involves {len(task.get('attendees', []))} attendee(s)")
        if task.get("location"):
            task_info.append(f"   Context: Location: {task.get('location')}")
        
        if task.get("is_critical"):
            task_info.append("   ⚠️ CRITICAL - Must be scheduled early")
        
        if task.get("is_urgent"):
            task_info.append("   🔴 URGENT - Time-sensitive")
        
        if task.get("location"):
            task_info.append(f"   Location: {task.get('location')}")
        
        if task.get("attendees"):
            task_info.append(f"   Attendees: {', '.join(task.get('attendees', []))}")
        
        prompt_parts.append("\n".join(task_info))
    
    if context.time_constraints:
        prompt_parts.append(f"\nGlobal Time Constraints: {json.dumps(context.time_constraints)}")
    
    prompt_parts.append(
        "\nIMPORTANT: Include ALL tasks in your plan. Do not exclude any tasks, even if they have 'normal' priority. "
        "Create a daily plan that respects time constraints, prioritizes critical/urgent tasks, "
        "and matches task complexity to the user's energy level when possible. "
        "Every task provided must appear in the final plan."
    )
    
    return "\n".join(prompt_parts)


def _generate_action_plan_for_task(task: Dict, user_id: Optional[str] = None) -> List[str]:
    """
    Generate actionable steps for a task using ChatGPT
    This is called when LLM planner doesn't include action_plan or for missing tasks
    
    Args:
        task: Task dictionary with title, description, etc.
        user_id: Optional user ID for logging
        
    Returns:
        List of actionable steps (3-7 steps)
    """
    try:
        title = task.get("title", "Unknown Task")
        description = task.get("description", "") or ""
        duration_minutes = 0
        
        # Calculate duration if times are available
        if task.get("start_time") and task.get("end_time"):
            try:
                start = datetime.fromisoformat(task.get("start_time").replace("Z", "+00:00"))
                end = datetime.fromisoformat(task.get("end_time").replace("Z", "+00:00"))
                duration_minutes = int((end - start).total_seconds() / 60)
            except:
                pass
        
        system_prompt = """You are an expert at breaking down tasks into actionable steps.
Given a task title and description, create a concrete action plan with 3-7 specific, executable steps.
Each step should be:
- Specific and actionable (e.g., "Draft outline with 3 main sections" not "Work on outline")
- Ordered logically (first step first)
- Appropriate for the task complexity and time available
- Clear enough that someone could execute it immediately

Return a JSON object with an "action_plan" array of step strings."""
        
        user_prompt = f"""Task: {title}
Description: {description[:500] if description else "No description provided"}
Estimated Duration: {duration_minutes} minutes

Break this task down into 3-7 actionable steps. Return JSON with:
{{
  "action_plan": ["step 1", "step 2", "step 3", ...]
}}"""
        
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
        except Exception:
            # Fallback to gpt-3.5-turbo
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
        
        result = json.loads(response.choices[0].message.content)
        action_plan = result.get("action_plan", [])
        
        # Ensure we have at least some steps
        if not action_plan or len(action_plan) == 0:
            # Fallback to simple steps
            action_plan = [
                f"Review the task: {title}",
                "Gather necessary information and resources",
                "Execute the task",
                "Review and finalize"
            ]
        
        return action_plan[:7]  # Limit to 7 steps max
        
    except Exception as e:
        StructuredLogger.log_event(
            "action_plan_generation_failed",
            f"Failed to generate action plan for task: {task.get('title', 'Unknown')}",
            user_id=user_id or "unknown",
            metadata={"error": str(e), "task_title": task.get("title")},
            level="WARNING"
        )
        # Return simple fallback steps
        return [
            f"Review: {task.get('title', 'Task')}",
            "Gather necessary information",
            "Complete the task"
        ]


