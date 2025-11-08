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
from datetime import datetime
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
    
    workflow.add_edge("storage", END)
    
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
    }
    
    try:
        result = await ingestion_workflow.ainvoke(initial_state)
        return {
            "success": result["status"] in ["completed", "partial_success"],
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

