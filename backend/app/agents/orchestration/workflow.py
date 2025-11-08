"""LangGraph workflow for orchestrating the Perception Agent"""
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from app.agents.perception.calendar_ingestion import (
    fetch_calendar_events,
    CalendarIngestionError,
    get_user_credentials,
)
from app.agents.perception.nlp_extraction import (
    extract_raw_tasks_from_events,
    NLPExtractionError,
)
from app.models.task import RawTaskCreate
from app.database import supabase
from app.utils.monitoring import StructuredLogger, track_ingestion
from app.agents.cognition.encoding import store_task_context_embedding
from app.agents.cognition.planner import generate_daily_plan
from app.models.plan import PlanningContext
from datetime import datetime, date, timezone, timedelta
import uuid


class WorkflowState(TypedDict):
    """State schema for LangGraph workflow"""
    user_id: str
    oauth_token: Optional[str]
    calendar_events: List[dict]
    raw_tasks: List[RawTaskCreate]
    errors: List[str]
    status: str
    event_count: int
    energy_level: Optional[int]
    embeddings: List[dict]
    daily_plan: Optional[dict]
    plan_date: Optional[str]


async def auth_node(state: WorkflowState) -> WorkflowState:
    """Validate user session and retrieve OAuth tokens"""
    user_id = state["user_id"]
    
    try:
        StructuredLogger.log_event(
            "workflow_auth_start",
            "Starting authentication node",
            user_id=user_id,
        )
        
        # Check if user has OAuth tokens
        credentials = await get_user_credentials(user_id)
        
        if not credentials:
            return {
                **state,
                "status": "error",
                "errors": state["errors"] + ["No OAuth credentials found. Please connect your Google Calendar."],
            }
        
        return {
            **state,
            "status": "authenticated",
            "oauth_token": credentials.token,
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "auth_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Authentication failed: {str(e)}"],
        }


async def ingestion_node(state: WorkflowState) -> WorkflowState:
    """Fetch calendar events via Google API"""
    user_id = state["user_id"]
    
    try:
        StructuredLogger.log_event(
            "workflow_ingestion_start",
            "Starting calendar ingestion",
            user_id=user_id,
        )
        
        events = await fetch_calendar_events(user_id)
        
        return {
            **state,
            "status": "ingested",
            "calendar_events": events,
            "event_count": len(events),
        }
    except CalendarIngestionError as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "ingestion_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Ingestion failed: {str(e)}"],
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "ingestion_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Unexpected error during ingestion: {str(e)}"],
        }


async def extraction_node(state: WorkflowState) -> WorkflowState:
    """Transform events to Raw Tasks"""
    user_id = state["user_id"]
    events = state["calendar_events"]
    
    try:
        StructuredLogger.log_event(
            "workflow_extraction_start",
            "Starting NLP extraction",
            user_id=user_id,
            metadata={"event_count": len(events)},
        )
        
        raw_tasks = extract_raw_tasks_from_events(events, user_id)
        
        return {
            **state,
            "status": "extracted",
            "raw_tasks": raw_tasks,
        }
    except NLPExtractionError as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "extraction_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Extraction failed: {str(e)}"],
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "extraction_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Unexpected error during extraction: {str(e)}"],
        }


@track_ingestion
async def storage_node(state: WorkflowState) -> WorkflowState:
    """Save Raw Tasks to Supabase"""
    user_id = state["user_id"]
    raw_tasks = state["raw_tasks"]
    
    try:
        StructuredLogger.log_event(
            "workflow_storage_start",
            "Starting storage of raw tasks",
            user_id=user_id,
            metadata={"task_count": len(raw_tasks)},
        )
        
        stored_count = 0
        errors = []
        
        for raw_task in raw_tasks:
            try:
                # Check for duplicates (by source, title, and start_time)
                existing = supabase.table("raw_tasks").select("id").eq(
                    "user_id", user_id
                ).eq("source", raw_task.source).eq("title", raw_task.title).eq(
                    "start_time", raw_task.start_time.isoformat()
                ).execute()
                
                if existing.data:
                    # Skip duplicate
                    continue
                
                # Insert raw task
                task_data = {
                    "user_id": user_id,
                    "source": raw_task.source,
                    "title": raw_task.title,
                    "description": raw_task.description,
                    "start_time": raw_task.start_time.isoformat(),
                    "end_time": raw_task.end_time.isoformat(),
                    "attendees": raw_task.attendees,
                    "location": raw_task.location,
                    "recurrence_pattern": raw_task.recurrence_pattern,
                    "extracted_priority": raw_task.extracted_priority,
                    "is_critical": raw_task.is_critical,
                    "is_urgent": raw_task.is_urgent,
                    "raw_data": raw_task.raw_data,
                }
                
                supabase.table("raw_tasks").insert(task_data).execute()
                stored_count += 1
            except Exception as e:
                errors.append(f"Failed to store task '{raw_task.title}': {str(e)}")
                StructuredLogger.log_event(
                    "task_storage_error",
                    f"Failed to store task: {raw_task.title}",
                    user_id=user_id,
                    metadata={"error": str(e)},
                    level="WARNING"
                )
        
        if errors:
            state["errors"].extend(errors)
        
        StructuredLogger.log_event(
            "workflow_storage_complete",
            f"Stored {stored_count} raw tasks",
            user_id=user_id,
            metadata={"stored_count": stored_count, "error_count": len(errors)},
        )
        
        return {
            **state,
            "status": "completed" if not errors else "partial_success",
            "event_count": stored_count,
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "storage_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Storage failed: {str(e)}"],
        }


async def encoding_node(state: WorkflowState) -> WorkflowState:
    """Generate context embeddings for raw tasks"""
    user_id = state["user_id"]
    raw_tasks = state["raw_tasks"]
    energy_level = state.get("energy_level")
    plan_date_str = state.get("plan_date")
    
    if not energy_level or not plan_date_str:
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + ["Energy level and plan date required for encoding"],
        }
    
    try:
        StructuredLogger.log_event(
            "workflow_encoding_start",
            "Starting context encoding",
            user_id=user_id,
            metadata={"task_count": len(raw_tasks), "energy_level": energy_level},
        )
        
        plan_date = date.fromisoformat(plan_date_str)
        embeddings = []
        
        # Fetch stored tasks from database to get IDs
        for raw_task in raw_tasks:
            try:
                # Find task in database
                task_response = supabase.table("raw_tasks").select("id").eq(
                    "user_id", user_id
                ).eq("title", raw_task.title).eq(
                    "start_time", raw_task.start_time.isoformat()
                ).execute()
                
                if task_response.data:
                    task_id = task_response.data[0]["id"]
                    task_dict = {
                        "id": str(task_id),
                        "user_id": user_id,
                        "title": raw_task.title,
                        "description": raw_task.description,
                        "start_time": raw_task.start_time.isoformat(),
                        "end_time": raw_task.end_time.isoformat(),
                        "extracted_priority": raw_task.extracted_priority,
                        "is_critical": raw_task.is_critical,
                        "is_urgent": raw_task.is_urgent,
                        "attendees": raw_task.attendees,
                        "location": raw_task.location,
                    }
                    
                    # Store embedding
                    store_task_context_embedding(
                        user_id=user_id,
                        task_id=str(task_id),
                        raw_task=task_dict,
                        energy_level=energy_level,
                        priority=raw_task.extracted_priority,
                        plan_date=plan_date,
                    )
                    
                    embeddings.append({
                        "task_id": str(task_id),
                        "energy_level": energy_level,
                    })
            except Exception as e:
                StructuredLogger.log_event(
                    "encoding_error",
                    f"Failed to encode task: {raw_task.title}",
                    user_id=user_id,
                    metadata={"error": str(e)},
                    level="WARNING"
                )
        
        return {
            **state,
            "status": "encoded",
            "embeddings": embeddings,
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "encoding_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Encoding failed: {str(e)}"],
        }


async def planning_node(state: WorkflowState) -> WorkflowState:
    """Generate daily plan using LLM planner"""
    user_id = state["user_id"]
    raw_tasks = state["raw_tasks"]
    energy_level = state.get("energy_level")
    plan_date_str = state.get("plan_date")
    
    if not energy_level or not plan_date_str:
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + ["Energy level and plan date required for planning"],
        }
    
    try:
        StructuredLogger.log_event(
            "workflow_planning_start",
            "Starting daily plan generation",
            user_id=user_id,
            metadata={"task_count": len(raw_tasks), "energy_level": energy_level},
        )
        
        plan_date = date.fromisoformat(plan_date_str)
        next_day = plan_date + timedelta(days=1)
        
        # Convert raw tasks to dictionaries for planning context
        # Normalize task times to be on plan_date in local timezone
        task_dicts = []
        for raw_task in raw_tasks:
            # Fetch task ID from database
            task_response = supabase.table("raw_tasks").select("id").eq(
                "user_id", user_id
            ).eq("title", raw_task.title).eq(
                "start_time", raw_task.start_time.isoformat()
            ).execute()
            
            if task_response.data:
                task_id = task_response.data[0]["id"]
                
                # Check if this is an all-day task
                raw_data = raw_task.raw_data or {}
                start_data = raw_data.get("start", {})
                is_all_day = "date" in start_data  # All-day events use "date" instead of "dateTime"
                
                # Normalize start_time and end_time to be on plan_date
                # The issue: tasks stored in UTC might represent different local dates
                # Solution: Extract the LOCAL time component and apply it to plan_date
                if raw_task.start_time.tzinfo:
                    # Convert to UTC first
                    start_utc = raw_task.start_time.astimezone(timezone.utc)
                    end_utc = raw_task.end_time.astimezone(timezone.utc)
                    
                    # Use the original UTC times as-is - they already represent the correct local times
                    # The frontend will convert UTC to local time for display
                    # No normalization needed - preserve the actual UTC times from the database
                    normalized_start = start_utc
                    normalized_end = end_utc
                else:
                    # No timezone - assume UTC
                    normalized_start = raw_task.start_time
                    normalized_end = raw_task.end_time
                    if normalized_end <= normalized_start:
                        duration = raw_task.end_time - raw_task.start_time
                        normalized_end = normalized_start + duration
                
                task_dicts.append({
                    "id": str(task_id),
                    "user_id": user_id,
                    "title": raw_task.title,
                    "description": raw_task.description,
                    "start_time": normalized_start.isoformat(),
                    "end_time": normalized_end.isoformat(),
                    "extracted_priority": raw_task.extracted_priority,
                    "is_critical": raw_task.is_critical,
                    "is_urgent": raw_task.is_urgent,
                    "is_all_day": is_all_day,  # Pass all-day flag to planner
                    "attendees": raw_task.attendees,
                    "location": raw_task.location,
                })
        
        if not task_dicts:
            return {
                **state,
                "status": "error",
                "errors": state["errors"] + ["No tasks found for planning"],
            }
        
        # Create planning context
        context = PlanningContext(
            raw_tasks=task_dicts,
            energy_level=energy_level,
            plan_date=plan_date,
        )
        
        # Generate plan
        daily_plan = generate_daily_plan(context)
        
        # Store plan in database
        # Convert tasks to dict with proper serialization (UUIDs and datetimes to strings)
        tasks_data = []
        for task in daily_plan.tasks:
            task_dict = {
                "task_id": str(task.task_id),
                "predicted_start": task.predicted_start.isoformat(),
                "predicted_end": task.predicted_end.isoformat(),
                "priority_score": task.priority_score,
                "title": task.title,
                "is_critical": task.is_critical,
                "is_urgent": task.is_urgent,
            }
            tasks_data.append(task_dict)
        
        plan_data = {
            "user_id": user_id,
            "plan_date": plan_date.isoformat(),
            "tasks": tasks_data,
            "energy_level": energy_level,
            "status": "active",
        }
        
        # Check if plan already exists for this date
        existing = supabase.table("daily_plans").select("id").eq(
            "user_id", user_id
        ).eq("plan_date", plan_date.isoformat()).execute()
        
        if existing.data:
            # Update existing plan
            supabase.table("daily_plans").update(plan_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            # Create new plan
            supabase.table("daily_plans").insert(plan_data).execute()
        
        StructuredLogger.log_event(
            "workflow_planning_complete",
            f"Generated daily plan with {len(daily_plan.tasks)} tasks",
            user_id=user_id,
            metadata={"task_count": len(daily_plan.tasks)},
        )
        
        return {
            **state,
            "status": "planned",
            "daily_plan": daily_plan.dict(),
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "planning_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Planning failed: {str(e)}"],
        }


def should_continue(state: WorkflowState) -> str:
    """Determine next node based on state"""
    if state["status"] == "error":
        return "end"
    elif state["status"] == "authenticated":
        return "ingestion"
    elif state["status"] == "ingested":
        return "extraction"
    elif state["status"] == "extracted":
        return "storage"
    elif state["status"] == "completed" or state["status"] == "partial_success":
        # Check if we have plan_date and energy_level for encoding/planning
        if state.get("plan_date") and state.get("energy_level"):
            return "encoding"
        else:
            return "end"
    elif state["status"] == "encoded":
        return "planning"
    else:
        return "end"


# Create workflow graph
def create_ingestion_workflow():
    """Create and return the LangGraph workflow"""
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("auth", auth_node)
    workflow.add_node("ingestion", ingestion_node)
    workflow.add_node("extraction", extraction_node)
    workflow.add_node("storage", storage_node)
    workflow.add_node("encoding", encoding_node)
    workflow.add_node("planning", planning_node)
    
    # Set entry point
    workflow.set_entry_point("auth")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "auth",
        should_continue,
        {
            "ingestion": "ingestion",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "ingestion",
        should_continue,
        {
            "extraction": "extraction",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "extraction",
        should_continue,
        {
            "storage": "storage",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "storage",
        should_continue,
        {
            "encoding": "encoding",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "encoding",
        should_continue,
        {
            "planning": "planning",
            "end": END,
        }
    )
    
    workflow.add_edge("planning", END)
    
    return workflow.compile()


# Global workflow instance
ingestion_workflow = create_ingestion_workflow()


async def run_ingestion_workflow(user_id: str) -> dict:
    """Run the complete ingestion workflow"""
    initial_state: WorkflowState = {
        "user_id": user_id,
        "oauth_token": None,
        "calendar_events": [],
        "raw_tasks": [],
        "errors": [],
        "status": "started",
        "event_count": 0,
        "energy_level": None,
        "embeddings": [],
        "daily_plan": None,
        "plan_date": None,
    }
    
    try:
        result = await ingestion_workflow.ainvoke(initial_state)
        return {
            "success": result["status"] in ["completed", "partial_success", "planned"],
            "status": result["status"],
            "event_count": result.get("event_count", 0),
            "errors": result.get("errors", []),
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "run_ingestion_workflow"})
        return {
            "success": False,
            "status": "error",
            "event_count": 0,
            "errors": [str(e)],
        }


async def run_planning_workflow(user_id: str, plan_date: date, energy_level: Optional[int] = None) -> dict:
    """Run planning workflow for a specific date"""
    from datetime import datetime
    
    # Get energy level for date if not provided
    if not energy_level:
        energy_response = supabase.table("daily_energy_levels").select("*").eq(
            "user_id", user_id
        ).eq("date", plan_date.isoformat()).execute()
        
        if energy_response.data:
            energy_level = energy_response.data[0]["energy_level"]
        else:
            # Use default energy level (3) if not set
            energy_level = 3
    
    # Fetch raw tasks for the plan date
    # Use date string comparison to avoid timezone issues
    plan_date_str = plan_date.isoformat()
    
    # Query tasks where the LOCAL date part of start_time matches plan_date
    # Tasks are stored in UTC, but represent local times
    # For PST (UTC-8), Nov 8 local time spans from Nov 8 08:00 UTC to Nov 9 08:00 UTC
    # For EST (UTC-5), Nov 8 local time spans from Nov 8 05:00 UTC to Nov 9 05:00 UTC
    # We'll use a wider range to cover all US timezones: Nov 8 04:00 UTC to Nov 9 08:00 UTC
    # This covers PST (-8) to EST (-5) timezones
    from datetime import timedelta
    next_day = plan_date + timedelta(days=1)
    next_day_str = next_day.isoformat()
    
    # Query range: start from 8 AM UTC (covers start of day in PST)
    # Tasks stored as 00:00-08:00 UTC are likely previous day in PST, exclude them
    # End: 8 AM UTC next day (covers end of day in PST)
    start_query = f"{plan_date_str}T08:00:00Z"  # 8 AM UTC = Nov 8 midnight PST
    end_query = f"{next_day_str}T08:00:00Z"     # 8 AM UTC next day = Nov 9 midnight PST
    
    StructuredLogger.log_event(
        "planning_fetch_tasks",
        f"Fetching tasks for plan date {plan_date_str}",
        user_id=user_id,
        metadata={
            "plan_date": plan_date_str,
            "query_start": start_query,
            "query_end": end_query
        }
    )
    
    tasks_response = supabase.table("raw_tasks").select("*").eq(
        "user_id", user_id
    ).gte("start_time", start_query).lt("start_time", end_query).execute()
    
    # Log fetched tasks
    if tasks_response.data:
        StructuredLogger.log_event(
            "planning_tasks_fetched",
            f"Fetched {len(tasks_response.data)} tasks for plan",
            user_id=user_id,
            metadata={
                "task_count": len(tasks_response.data),
                "task_titles": [t.get("title", "Unknown") for t in tasks_response.data[:5]],  # First 5 titles
                "task_dates": [
                    # Convert UTC date to local date for logging (PST = UTC-8)
                    # Extract date from ISO string and show both UTC and inferred PST date
                    f"{t.get('start_time', 'Unknown')[:10]} UTC" 
                    for t in tasks_response.data[:5]
                ]
            }
        )
    
    if not tasks_response.data:
        return {
            "success": False,
            "status": "error",
            "errors": ["No tasks found for the specified date"],
        }
    
    # Convert to RawTaskCreate format
    # Filter out all-day tasks that are for the next day (they start at midnight UTC on next_day)
    from app.models.task import RawTaskCreate
    raw_tasks = []
    for task_data in tasks_response.data:
        # Check if this is an all-day task by looking at raw_data
        raw_data = task_data.get("raw_data", {})
        start_data = raw_data.get("start", {})
        is_all_day = "date" in start_data  # All-day events use "date" instead of "dateTime"
        
        # Parse start_time to check the date
        start_time = datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00"))
        start_date_utc = start_time.date()
        
        # Exclude all-day tasks that start on next_day (they're for tomorrow, not today)
        if is_all_day and start_date_utc == next_day:
            StructuredLogger.log_event(
                "planning_skip_all_day_next_day",
                f"Skipping all-day task '{task_data.get('title')}' for next day",
                user_id=user_id,
                metadata={"task_title": task_data.get("title"), "start_date": str(start_date_utc)},
            )
            continue
        
        raw_tasks.append(RawTaskCreate(
            source=task_data["source"],
            title=task_data["title"],
            description=task_data.get("description"),
            start_time=start_time,
            end_time=datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00")),
            attendees=task_data.get("attendees", []),
            location=task_data.get("location"),
            recurrence_pattern=task_data.get("recurrence_pattern"),
            extracted_priority=task_data.get("extracted_priority"),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            raw_data=raw_data,
        ))
    
    # Create initial state for planning workflow
    initial_state: WorkflowState = {
        "user_id": user_id,
        "oauth_token": None,
        "calendar_events": [],
        "raw_tasks": raw_tasks,
        "errors": [],
        "status": "extracted",  # Skip to encoding/planning
        "event_count": len(raw_tasks),
        "energy_level": energy_level,
        "embeddings": [],
        "daily_plan": None,
        "plan_date": plan_date.isoformat(),
    }
    
    try:
        # Run encoding and planning nodes
        state = await encoding_node(initial_state)
        if state["status"] == "error":
            return {
                "success": False,
                "status": "error",
                "errors": state.get("errors", []),
            }
        
        state = await planning_node(state)
        if state["status"] == "error":
            return {
                "success": False,
                "status": "error",
                "errors": state.get("errors", []),
            }
        
        return {
            "success": True,
            "status": "planned",
            "errors": [],
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "run_planning_workflow"})
        return {
            "success": False,
            "status": "error",
            "errors": [str(e)],
        }

