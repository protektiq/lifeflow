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
    extract_raw_tasks_from_emails,
    NLPExtractionError,
)
from app.agents.perception.email_ingestion import (
    fetch_gmail_messages,
    EmailIngestionError,
)
from app.models.task import RawTaskCreate
from app.database import supabase
from app.utils.monitoring import StructuredLogger, track_ingestion
from app.agents.cognition.encoding import (
    store_task_context_embedding,
    store_email_snippet_embedding,
    store_task_note_embedding,
    store_conversation_embedding,
)
from app.agents.cognition.planner import generate_daily_plan
from app.models.plan import PlanningContext
from datetime import datetime, date, timezone, timedelta
from uuid import UUID
import uuid


class WorkflowState(TypedDict):
    """State schema for LangGraph workflow"""
    user_id: str
    oauth_token: Optional[str]
    calendar_events: List[dict]
    email_messages: List[dict]
    email_messages_for_encoding: Optional[List[dict]]  # Emails kept for encoding after task creation
    email_tasks: List[RawTaskCreate]
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


async def email_ingestion_node(state: WorkflowState) -> WorkflowState:
    """Fetch emails via Gmail API"""
    user_id = state["user_id"]
    
    try:
        StructuredLogger.log_event(
            "workflow_email_ingestion_start",
            "Starting email ingestion",
            user_id=user_id,
        )
        
        # Fetch unread and flagged emails (excluding spam)
        emails = await fetch_gmail_messages(user_id, query='is:unread OR is:flagged -is:spam')
        
        return {
            **state,
            "status": "email_ingested",
            "email_messages": emails,
        }
    except EmailIngestionError as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "email_ingestion_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Email ingestion failed: {str(e)}"],
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "email_ingestion_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Unexpected error during email ingestion: {str(e)}"],
        }


async def email_extraction_node(state: WorkflowState) -> WorkflowState:
    """Transform emails to Raw Tasks"""
    user_id = state["user_id"]
    emails = state.get("email_messages", [])
    
    try:
        StructuredLogger.log_event(
            "workflow_email_extraction_start",
            "Starting email NLP extraction",
            user_id=user_id,
            metadata={"email_count": len(emails)},
        )
        
        email_tasks = extract_raw_tasks_from_emails(emails, user_id)
        
        # Store email messages in state for later encoding (after task creation)
        # This allows us to link email snippets to their created tasks
        return {
            **state,
            "status": "email_extracted",
            "email_tasks": email_tasks,
            "email_messages_for_encoding": emails,  # Keep emails for encoding after task creation
        }
    except NLPExtractionError as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "email_extraction_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Email extraction failed: {str(e)}"],
        }
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "node": "email_extraction_node"})
        return {
            **state,
            "status": "error",
            "errors": state["errors"] + [f"Unexpected error during email extraction: {str(e)}"],
        }


async def extraction_node(state: WorkflowState) -> WorkflowState:
    """Transform events to Raw Tasks and merge with email tasks"""
    user_id = state["user_id"]
    events = state.get("calendar_events", [])
    email_tasks = state.get("email_tasks", [])
    
    try:
        StructuredLogger.log_event(
            "workflow_extraction_start",
            "Starting NLP extraction",
            user_id=user_id,
            metadata={"event_count": len(events), "email_task_count": len(email_tasks)},
        )
        
        calendar_tasks = extract_raw_tasks_from_events(events, user_id)
        
        # Merge calendar and email tasks
        all_tasks = calendar_tasks + email_tasks
        
        return {
            **state,
            "status": "extracted",
            "raw_tasks": all_tasks,
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
                # Check for duplicates
                # For emails, use message_id from raw_data to prevent duplicates
                # For calendar events, use source + title + start_time
                existing = None
                if raw_task.source == "gmail" and raw_task.raw_data:
                    # Try to get message ID from raw_data (could be nested)
                    message_id = None
                    if isinstance(raw_task.raw_data, dict):
                        message_id = raw_task.raw_data.get("id") or raw_task.raw_data.get("raw_data", {}).get("id")
                    
                    if message_id:
                        # Check by email message ID (most reliable for emails)
                        # Fetch all gmail tasks and check raw_data in Python (JSONB queries can be complex)
                        all_gmail_tasks = supabase.table("raw_tasks").select("id, raw_data").eq(
                            "user_id", user_id
                        ).eq("source", "gmail").execute()
                        
                        for task in all_gmail_tasks.data:
                            task_raw_data = task.get("raw_data", {})
                            task_msg_id = None
                            if isinstance(task_raw_data, dict):
                                task_msg_id = task_raw_data.get("id") or task_raw_data.get("raw_data", {}).get("id")
                            
                            if task_msg_id == message_id:
                                # Found duplicate - create mock response object
                                class MockResponse:
                                    def __init__(self, data):
                                        self.data = data
                                existing = MockResponse([task])
                                break
                
                # Fallback to title + start_time check if no message_id
                if not existing or not existing.data:
                    existing = supabase.table("raw_tasks").select("id").eq(
                        "user_id", user_id
                    ).eq("source", raw_task.source).eq("title", raw_task.title).eq(
                        "start_time", raw_task.start_time.isoformat()
                    ).execute()
                
                if existing.data:
                    # Found duplicate - update existing task if it's an email (to fix priority/spam issues)
                    existing_id = existing.data[0].get("id")
                    
                    if raw_task.source == "gmail":
                        # For emails, update the existing task to fix any classification issues
                        # This allows re-processing to fix spam/priority misclassifications
                        update_data = {
                            "extracted_priority": raw_task.extracted_priority,
                            "is_spam": raw_task.is_spam,
                            "spam_reason": raw_task.spam_reason,
                            "spam_score": raw_task.spam_score,
                            "is_critical": raw_task.is_critical,
                            "is_urgent": raw_task.is_urgent,
                            "updated_at": datetime.utcnow().isoformat(),
                        }
                        
                        # Only update if there are actual changes (avoid unnecessary updates)
                        supabase.table("raw_tasks").update(update_data).eq("id", existing_id).execute()
                        
                        StructuredLogger.log_event(
                            "task_duplicate_updated",
                            f"Updated duplicate email task: {raw_task.title}",
                            user_id=user_id,
                            metadata={
                                "title": raw_task.title,
                                "existing_id": existing_id,
                                "new_priority": raw_task.extracted_priority,
                                "new_is_spam": raw_task.is_spam,
                            },
                        )
                    else:
                        # For calendar events, skip duplicates
                        StructuredLogger.log_event(
                            "task_duplicate_skipped",
                            f"Skipping duplicate task: {raw_task.title}",
                            user_id=user_id,
                            metadata={
                                "title": raw_task.title,
                                "source": raw_task.source,
                                "existing_id": existing_id,
                            },
                        )
                    continue
                
                # Insert raw task
                # Ensure datetimes are timezone-aware and converted to UTC for storage
                start_time_utc = raw_task.start_time
                end_time_utc = raw_task.end_time
                
                # Convert to UTC if timezone-aware, otherwise assume UTC
                if start_time_utc.tzinfo is None:
                    # Naive datetime - assume it's already in UTC
                    start_time_utc = start_time_utc.replace(tzinfo=timezone.utc)
                else:
                    # Timezone-aware - convert to UTC
                    start_time_utc = start_time_utc.astimezone(timezone.utc)
                
                if end_time_utc.tzinfo is None:
                    end_time_utc = end_time_utc.replace(tzinfo=timezone.utc)
                else:
                    end_time_utc = end_time_utc.astimezone(timezone.utc)
                
                task_data = {
                    "user_id": user_id,
                    "source": raw_task.source,
                    "title": raw_task.title,
                    "description": raw_task.description,
                    "start_time": start_time_utc.isoformat(),
                    "end_time": end_time_utc.isoformat(),
                    "attendees": raw_task.attendees,
                    "location": raw_task.location,
                    "recurrence_pattern": raw_task.recurrence_pattern,
                    "extracted_priority": raw_task.extracted_priority,
                    "is_critical": raw_task.is_critical,
                    "is_urgent": raw_task.is_urgent,
                    "is_spam": raw_task.is_spam,
                    "spam_reason": raw_task.spam_reason,
                    "spam_score": raw_task.spam_score,
                    "raw_data": raw_task.raw_data,
                }
                
                result = supabase.table("raw_tasks").insert(task_data).execute()
                stored_count += 1
                
                # Get the inserted task ID
                inserted_task_id = None
                if result.data and len(result.data) > 0:
                    inserted_task_id = result.data[0].get("id")
                
                # Store task note/description embedding if description exists
                if inserted_task_id and raw_task.description:
                    try:
                        store_task_note_embedding(
                            user_id=user_id,
                            task_id=str(inserted_task_id),
                            note_text=raw_task.description,
                            metadata={
                                "source": raw_task.source,
                                "title": raw_task.title,
                            }
                        )
                    except Exception as e:
                        StructuredLogger.log_event(
                            "task_note_encoding_error",
                            f"Failed to encode task note: {raw_task.title}",
                            user_id=user_id,
                            metadata={"error": str(e), "task_id": str(inserted_task_id)},
                            level="WARNING"
                        )
                
            except Exception as e:
                errors.append(f"Failed to store task '{raw_task.title}': {str(e)}")
                StructuredLogger.log_event(
                    "task_storage_error",
                    f"Failed to store task: {raw_task.title}",
                    user_id=user_id,
                    metadata={"error": str(e)},
                    level="WARNING"
                )
        
        # Encode email snippets and conversations after tasks are stored
        email_messages = state.get("email_messages_for_encoding", [])
        if email_messages:
            # Create a mapping of email_id to task_id for linking
            email_to_task_map = {}
            for raw_task in raw_tasks:
                if raw_task.source == "gmail" and raw_task.raw_data:
                    email_id = None
                    if isinstance(raw_task.raw_data, dict):
                        email_id = raw_task.raw_data.get("id") or raw_task.raw_data.get("raw_data", {}).get("id")
                    
                    if email_id:
                        # Find the task in database
                        try:
                            task_response = supabase.table("raw_tasks").select("id").eq(
                                "user_id", user_id
                            ).eq("title", raw_task.title).eq(
                                "start_time", raw_task.start_time.isoformat()
                            ).execute()
                            
                            if task_response.data:
                                task_id = task_response.data[0]["id"]
                                email_to_task_map[str(email_id)] = str(task_id)
                        except Exception:
                            pass  # Skip if we can't find the task
            
            # Store email snippet embeddings
            for email in email_messages:
                try:
                    email_id = email.get("id", "")
                    snippet = email.get("snippet", "")
                    thread_id = email.get("thread_id", "")
                    
                    if snippet and email_id:
                        task_id = email_to_task_map.get(str(email_id), "")
                        if task_id:  # Only store if we have a linked task
                            store_email_snippet_embedding(
                                user_id=user_id,
                                task_id=task_id,
                                email_id=email_id,
                                snippet=snippet,
                                thread_id=thread_id if thread_id else None,
                            )
                except Exception as e:
                    StructuredLogger.log_event(
                        "email_snippet_encoding_error",
                        f"Failed to encode email snippet: {email.get('id', 'unknown')}",
                        user_id=user_id,
                        metadata={"error": str(e), "email_id": email.get("id", "unknown")},
                        level="WARNING"
                    )
            
            # Group emails by thread_id and create conversation embeddings
            thread_groups = {}
            for email in email_messages:
                thread_id = email.get("thread_id", "")
                if thread_id:
                    if thread_id not in thread_groups:
                        thread_groups[thread_id] = []
                    thread_groups[thread_id].append(email)
            
            # Create conversation embeddings for each thread
            for thread_id, thread_emails in thread_groups.items():
                if len(thread_emails) > 1:  # Only create conversation embeddings for threads with multiple emails
                    try:
                        # Combine snippets and subjects from all emails in thread
                        conversation_parts = []
                        email_ids = []
                        task_ids = []
                        
                        for email in thread_emails:
                            email_id = email.get("id", "")
                            email_ids.append(email_id)
                            task_id = email_to_task_map.get(str(email_id), "")
                            if task_id:
                                task_ids.append(task_id)
                            
                            if email.get("snippet"):
                                conversation_parts.append(f"Subject: {email.get('subject', '')}\n{email.get('snippet', '')}")
                        
                        conversation_text = "\n\n---\n\n".join(conversation_parts)
                        
                        if conversation_text:
                            store_conversation_embedding(
                                user_id=user_id,
                                thread_id=thread_id,
                                conversation_text=conversation_text,
                                email_ids=email_ids if email_ids else None,
                                task_ids=task_ids if task_ids else None,
                            )
                    except Exception as e:
                        StructuredLogger.log_event(
                            "conversation_encoding_error",
                            f"Failed to encode conversation thread: {thread_id}",
                            user_id=user_id,
                            metadata={"error": str(e), "thread_id": thread_id},
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
        skipped_spam_count = 0
        for raw_task in raw_tasks:
            # Skip spam/promotional emails - they should not appear in daily plan
            if raw_task.is_spam:
                skipped_spam_count += 1
                StructuredLogger.log_event(
                    "planning_skip_spam_task",
                    f"Skipping spam task '{raw_task.title}' from daily plan",
                    user_id=user_id,
                    metadata={
                        "task_title": raw_task.title,
                        "spam_reason": raw_task.spam_reason,
                        "spam_score": raw_task.spam_score,
                    },
                )
                continue
            
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
            StructuredLogger.log_event(
                "planning_no_tasks_after_filtering",
                f"No tasks remaining after filtering (skipped {skipped_spam_count} spam tasks)",
                user_id=user_id,
                metadata={
                    "skipped_spam": skipped_spam_count,
                    "original_task_count": len(raw_tasks),
                },
            )
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
                "action_plan": task.action_plan,  # Include action plan steps
                "description": task.description,  # Include original description
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
        # Start both calendar and email ingestion in parallel
        # We'll use conditional routing to handle both paths
        return "ingestion"  # Calendar ingestion first, then email ingestion
    elif state["status"] == "ingested":
        # After calendar ingestion, start email ingestion
        return "email_ingestion"
    elif state["status"] == "email_ingested":
        # After email ingestion, extract tasks from emails
        return "email_extraction"
    elif state["status"] == "email_extracted":
        # After email extraction, merge with calendar tasks
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
    workflow.add_node("email_ingestion", email_ingestion_node)
    workflow.add_node("email_extraction", email_extraction_node)
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
            "email_ingestion": "email_ingestion",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "email_ingestion",
        should_continue,
        {
            "email_extraction": "email_extraction",
            "end": END,
        }
    )
    
    workflow.add_conditional_edges(
        "email_extraction",
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
        "email_messages": [],
        "email_tasks": [],
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
    # We need to query a wider range and then filter by local date
    # Use a range that covers all possible timezones: from midnight UTC of plan_date to midnight UTC of next_day+1
    from datetime import timedelta
    next_day = plan_date + timedelta(days=1)
    day_after_next = plan_date + timedelta(days=2)
    
    # Query range: from start of plan_date UTC to start of day_after_next UTC
    # This ensures we capture all tasks regardless of timezone
    start_query = f"{plan_date_str}T00:00:00Z"
    end_query = f"{day_after_next.isoformat()}T00:00:00Z"
    
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
    
    # Fetch tasks, excluding spam/promotional emails
    tasks_response = supabase.table("raw_tasks").select("*").eq(
        "user_id", user_id
    ).eq("is_spam", False).gte("start_time", start_query).lt("start_time", end_query).execute()
    
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
    # Filter tasks by local date and collect reminders separately
    from app.models.task import RawTaskCreate
    raw_tasks = []
    reminders = []  # Collect reminders separately instead of filtering them out
    skipped_previous_day = 0
    skipped_spam = 0
    
    for task_data in tasks_response.data:
        # Skip spam/promotional emails - they should not appear in daily plan
        is_spam = task_data.get("is_spam", False)
        if is_spam:
            skipped_spam += 1
            StructuredLogger.log_event(
                "planning_skip_spam",
                f"Skipping spam task '{task_data.get('title')}' from daily plan",
                user_id=user_id,
                metadata={
                    "task_title": task_data.get("title"),
                    "spam_reason": task_data.get("spam_reason"),
                    "spam_score": task_data.get("spam_score"),
                },
            )
            continue
        
        # Check if this is a reminder (Google Calendar reminders have eventType or are very short events)
        raw_data = task_data.get("raw_data", {})
        event_type = raw_data.get("eventType", "default")
        start_data = raw_data.get("start", {})
        
        # Check if it's an all-day event
        is_all_day_event = "date" in start_data
        
        # Check if it's a reminder: 
        # 1. eventType is "reminder"
        # 2. All-day events with no attendees/location (likely reminders)
        # 3. Very short events (< 5 minutes) with no attendees/location and "reminder" in title
        start_time = datetime.fromisoformat(task_data["start_time"].replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(task_data["end_time"].replace("Z", "+00:00"))
        duration = end_time - start_time
        
        title_lower = task_data.get("title", "").lower()
        has_attendees = task_data.get("attendees") and len(task_data.get("attendees", [])) > 0
        has_location = bool(task_data.get("location"))
        
        # Check if already converted from reminder - if so, treat as regular task
        is_converted_reminder = raw_data.get("converted_from_reminder", False)
        
        is_reminder = (
            not is_converted_reminder and  # Don't treat converted reminders as reminders
            (event_type == "reminder" or
            (is_all_day_event and not has_attendees and not has_location) or  # All-day events without attendees/location are likely reminders
            (duration.total_seconds() < 300 and  # Less than 5 minutes
             not has_attendees and
             not has_location and
             "reminder" in title_lower))
        )
        
        if is_reminder:
            # Check if reminder is for the plan_date before adding it
            reminder_date_matches = False
            
            if is_all_day_event:
                all_day_date_str = start_data.get("date")
                if all_day_date_str:
                    all_day_date = date.fromisoformat(all_day_date_str)
                    reminder_date_matches = all_day_date == plan_date
            else:
                # For timed reminders, check local date
                date_time_str = start_data.get("dateTime", "")
                if date_time_str:
                    try:
                        date_part = date_time_str.split('T')[0]
                        if len(date_part) == 10:
                            local_date = date.fromisoformat(date_part)
                            reminder_date_matches = local_date == plan_date
                    except (ValueError, AttributeError, IndexError):
                        # Fallback to UTC date check
                        reminder_date_matches = start_time.date() == plan_date or start_time.date() == next_day
            
            if reminder_date_matches:
                # Store reminder data for display
                reminders.append({
                    "id": task_data.get("id"),
                    "title": task_data.get("title"),
                    "description": task_data.get("description"),
                    "start_time": task_data.get("start_time"),
                    "end_time": task_data.get("end_time"),
                    "is_all_day": is_all_day_event,
                    "raw_data": raw_data,
                })
                StructuredLogger.log_event(
                    "planning_collected_reminder",
                    f"Collected reminder '{task_data.get('title')}' for plan date",
                    user_id=user_id,
                    metadata={
                        "task_title": task_data.get("title"), 
                        "event_type": event_type,
                        "is_all_day_event": is_all_day_event,
                    },
                )
            # Skip reminder - don't add to raw_tasks
            continue
        
        # Check if this is an all-day task (we already extracted start_data above)
        is_all_day = is_all_day_event  # All-day events use "date" instead of "dateTime"
        
        # For all-day tasks, check the date field directly
        if is_all_day:
            all_day_date_str = start_data.get("date")
            if all_day_date_str:
                all_day_date = date.fromisoformat(all_day_date_str)
                if all_day_date != plan_date:
                    skipped_previous_day += 1
                    StructuredLogger.log_event(
                        "planning_skip_all_day_wrong_date",
                        f"Skipping all-day task '{task_data.get('title')}' for date {all_day_date_str}",
                        user_id=user_id,
                        metadata={"task_title": task_data.get("title"), "all_day_date": all_day_date_str, "plan_date": plan_date_str},
                    )
                    continue
        
        # For timed events, check if the LOCAL date matches plan_date
        # Google Calendar events store the original local time in raw_data
        # We should use that to determine the correct date, not the UTC-stored time
        if not is_all_day:
            # Try to extract the local date from raw_data
            # Google Calendar events have dateTime in the user's timezone
            date_time_str = start_data.get("dateTime", "")
            local_date = None
            
            # Log raw_data structure for debugging
            StructuredLogger.log_event(
                "planning_checking_task_date",
                f"Checking task date for '{task_data.get('title')}'",
                user_id=user_id,
                metadata={
                    "task_title": task_data.get("title"),
                    "start_time_utc": task_data.get("start_time"),
                    "raw_data_start": str(start_data),
                    "date_time_str": date_time_str,
                    "plan_date": plan_date_str
                },
                level="DEBUG"
            )
            
            # Extract the local date from the dateTime string BEFORE parsing/converting to UTC
            # Format is typically: "2025-11-08T16:00:00-08:00" or "2025-11-09T01:00:00Z"
            # We need to extract the date part (YYYY-MM-DD) directly from the string
            if date_time_str:
                try:
                    # Extract date part from the string (before the 'T')
                    # This gives us the local date without timezone conversion
                    date_part = date_time_str.split('T')[0]
                    if len(date_part) == 10:  # YYYY-MM-DD format
                        local_date = date.fromisoformat(date_part)
                        StructuredLogger.log_event(
                            "planning_extracted_local_date",
                            f"Extracted local date {local_date} from dateTime string",
                            user_id=user_id,
                            metadata={
                                "task_title": task_data.get("title"),
                                "date_time_str": date_time_str,
                                "local_date": str(local_date),
                                "plan_date": plan_date_str
                            },
                            level="INFO"
                        )
                except (ValueError, AttributeError, IndexError) as e:
                    # If extraction fails, fall back to UTC date check
                    StructuredLogger.log_event(
                        "planning_local_date_extraction_failed",
                        f"Failed to extract local date from dateTime string",
                        user_id=user_id,
                        metadata={
                            "task_title": task_data.get("title"),
                            "date_time_str": date_time_str,
                            "error": str(e)
                        },
                        level="WARNING"
                    )
                    pass
            
            # If we couldn't get local date from raw_data, use UTC date as fallback
            # but be more conservative about filtering
            if local_date is None:
                start_date_utc = start_time.date()
                
                # If UTC date is before plan_date, skip (definitely from previous day)
                if start_date_utc < plan_date:
                    skipped_previous_day += 1
                    StructuredLogger.log_event(
                        "planning_skip_previous_day",
                        f"Skipping task '{task_data.get('title')}' from previous day (UTC date: {start_date_utc})",
                        user_id=user_id,
                        metadata={"task_title": task_data.get("title"), "start_date_utc": str(start_date_utc), "plan_date": plan_date_str},
                    )
                    continue
                
                # If UTC date is day_after_next or later, skip (from future day)
                if start_date_utc >= day_after_next:
                    skipped_previous_day += 1
                    StructuredLogger.log_event(
                        "planning_skip_future_day",
                        f"Skipping task '{task_data.get('title')}' from future day (UTC date: {start_date_utc})",
                        user_id=user_id,
                        metadata={"task_title": task_data.get("title"), "start_date_utc": str(start_date_utc), "plan_date": plan_date_str},
                    )
                    continue
                
                # For tasks on next_day UTC with early times (< 8 AM UTC), 
                # they're likely for next_day in most timezones, so skip
                if start_date_utc == next_day and start_time.hour < 8:
                    skipped_previous_day += 1
                    StructuredLogger.log_event(
                        "planning_skip_early_next_day",
                        f"Skipping task '{task_data.get('title')}' likely for next day (UTC: {start_time.isoformat()})",
                        user_id=user_id,
                        metadata={"task_title": task_data.get("title"), "start_time_utc": start_time.isoformat(), "plan_date": plan_date_str},
                    )
                    continue
            else:
                # Use the local date from raw_data - this is the most accurate
                if local_date != plan_date:
                    skipped_previous_day += 1
                    StructuredLogger.log_event(
                        "planning_skip_wrong_local_date",
                        f"Skipping task '{task_data.get('title')}' - local date {local_date} doesn't match plan_date {plan_date_str}",
                        user_id=user_id,
                        metadata={"task_title": task_data.get("title"), "local_date": str(local_date), "plan_date": plan_date_str},
                    )
                    continue
        
        raw_tasks.append(RawTaskCreate(
            source=task_data["source"],
            title=task_data["title"],
            description=task_data.get("description"),
            start_time=start_time,
            end_time=end_time,
            attendees=task_data.get("attendees", []),
            location=task_data.get("location"),
            recurrence_pattern=task_data.get("recurrence_pattern"),
            extracted_priority=task_data.get("extracted_priority"),
            is_critical=task_data.get("is_critical", False),
            is_urgent=task_data.get("is_urgent", False),
            raw_data=raw_data,
        ))
    
    # Log filtering results
    StructuredLogger.log_event(
        "planning_tasks_filtered",
        f"Filtered tasks: {len(raw_tasks)} included, {skipped_previous_day} from wrong day, {skipped_spam} spam filtered, {len(reminders)} reminders collected",
        user_id=user_id,
        metadata={
            "included_count": len(raw_tasks),
            "skipped_previous_day": skipped_previous_day,
            "skipped_spam": skipped_spam,
            "reminders_count": len(reminders),
        }
    )
    
    # Handle case where no tasks remain after filtering
    if not raw_tasks:
        StructuredLogger.log_event(
            "planning_no_tasks",
            f"No tasks remaining after filtering for plan date {plan_date_str}",
            user_id=user_id,
            metadata={
                "plan_date": plan_date_str,
                "skipped_previous_day": skipped_previous_day,
                "reminders_count": len(reminders),
            }
        )
        # Create an empty plan
        from app.models.plan import DailyPlan
        empty_plan = DailyPlan(
            user_id=UUID(user_id) if isinstance(user_id, str) else user_id,
            plan_date=plan_date,
            tasks=[],
            energy_level=energy_level,
            status="active"
        )
        
        # Store empty plan in database
        plan_data = {
            "user_id": user_id,
            "plan_date": plan_date.isoformat(),
            "tasks": [],
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
        
        return {
            "success": True,
            "status": "planned",
            "errors": [],
        }
    
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

