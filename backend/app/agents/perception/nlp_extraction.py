"""NLP extraction logic to parse calendar events into RawTask objects"""
from typing import List, Dict, Optional
from datetime import datetime
from dateutil import parser as date_parser
from app.models.task import RawTaskCreate
from app.utils.monitoring import StructuredLogger, error_handler
import re


class NLPExtractionError(Exception):
    """Custom exception for NLP extraction errors"""
    pass


def extract_priority_from_title(title: str) -> Optional[str]:
    """Extract priority indicator from event title"""
    title_lower = title.lower()
    
    # High priority keywords
    if any(keyword in title_lower for keyword in ['urgent', 'asap', 'important', 'critical', '!']):
        return "high"
    
    # Medium priority keywords
    if any(keyword in title_lower for keyword in ['meeting', 'call', 'review']):
        return "medium"
    
    # Low priority keywords
    if any(keyword in title_lower for keyword in ['optional', 'tentative', 'maybe']):
        return "low"
    
    return None


def parse_datetime(date_str: str, is_all_day: bool = False) -> datetime:
    """Parse datetime string from Google Calendar format"""
    try:
        if is_all_day:
            # All-day events have date only (YYYY-MM-DD)
            return datetime.strptime(date_str, "%Y-%m-%d")
        else:
            # Regular events have datetime with timezone
            return date_parser.parse(date_str)
    except Exception as e:
        StructuredLogger.log_event(
            "datetime_parse_error",
            f"Failed to parse datetime: {date_str}",
            metadata={"date_str": date_str, "is_all_day": is_all_day},
            level="WARNING"
        )
        raise NLPExtractionError(f"Failed to parse datetime: {str(e)}")


def extract_attendees(event: Dict) -> List[str]:
    """Extract attendee emails from event"""
    attendees = []
    
    if "attendees" in event:
        for attendee in event["attendees"]:
            email = attendee.get("email", "")
            if email:
                attendees.append(email)
    
    return attendees


def extract_recurrence_pattern(event: Dict) -> Optional[str]:
    """Extract recurrence pattern from event"""
    if "recurrence" in event and event["recurrence"]:
        # Return first recurrence rule (simplified)
        return event["recurrence"][0] if isinstance(event["recurrence"], list) else str(event["recurrence"])
    return None


@error_handler
def extract_raw_task_from_event(event: Dict, user_id: str) -> RawTaskCreate:
    """Extract RawTask from Google Calendar event"""
    try:
        # Extract basic information
        title = event.get("summary", "Untitled Event")
        description = event.get("description", "")
        location = event.get("location", "")
        
        # Extract start and end times
        start_data = event.get("start", {})
        end_data = event.get("end", {})
        
        is_all_day = "date" in start_data  # All-day events use "date" instead of "dateTime"
        
        start_time = parse_datetime(
            start_data.get("dateTime") or start_data.get("date", ""),
            is_all_day=is_all_day
        )
        end_time = parse_datetime(
            end_data.get("dateTime") or end_data.get("date", ""),
            is_all_day=is_all_day
        )
        
        # Extract attendees
        attendees = extract_attendees(event)
        
        # Extract recurrence pattern
        recurrence_pattern = extract_recurrence_pattern(event)
        
        # Extract priority from title
        extracted_priority = extract_priority_from_title(title)
        
        return RawTaskCreate(
            source="google_calendar",
            title=title,
            description=description if description else None,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            location=location if location else None,
            recurrence_pattern=recurrence_pattern,
            extracted_priority=extracted_priority,
            raw_data=event,
        )
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": user_id,
                "event_id": event.get("id", "unknown"),
                "function": "extract_raw_task_from_event"
            }
        )
        raise NLPExtractionError(f"Failed to extract task from event: {str(e)}")


@error_handler
def extract_raw_tasks_from_events(events: List[Dict], user_id: str) -> List[RawTaskCreate]:
    """Extract multiple RawTasks from a list of events"""
    raw_tasks = []
    errors = []
    
    for event in events:
        try:
            # Skip cancelled events
            if event.get("status") == "cancelled":
                continue
            
            raw_task = extract_raw_task_from_event(event, user_id)
            raw_tasks.append(raw_task)
        except Exception as e:
            errors.append({
                "event_id": event.get("id", "unknown"),
                "error": str(e),
            })
            StructuredLogger.log_event(
                "task_extraction_error",
                f"Failed to extract task from event {event.get('id', 'unknown')}",
                user_id=user_id,
                metadata={"error": str(e)},
                level="WARNING"
            )
    
    if errors:
        StructuredLogger.log_event(
            "batch_extraction_summary",
            f"Extracted {len(raw_tasks)} tasks with {len(errors)} errors",
            user_id=user_id,
            metadata={"success_count": len(raw_tasks), "error_count": len(errors)},
        )
    
    return raw_tasks

