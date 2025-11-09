"""NLP extraction logic to parse calendar events into RawTask objects"""
from typing import List, Dict, Optional
from datetime import datetime
from dateutil import parser as date_parser
from openai import OpenAI
from app.config import settings
from app.models.task import RawTaskCreate
from app.utils.monitoring import StructuredLogger, error_handler
import re
import json


class NLPExtractionError(Exception):
    """Custom exception for NLP extraction errors"""
    pass


# Initialize OpenAI client
openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)


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


def extract_task_with_chatgpt(event: Dict, user_id: str) -> Optional[Dict]:
    """
    Extract task information using ChatGPT
    
    Args:
        event: Calendar event dictionary
        user_id: User ID for logging
        
    Returns:
        Dictionary with extracted fields or None if extraction fails:
        - extracted_priority: "high", "medium", "low", or "normal"
        - is_critical: boolean
        - is_urgent: boolean
        - deadline: ISO datetime string if mentioned in description
        - task_complexity: "low", "medium", or "high"
        - reasoning: brief explanation of extraction decisions
    """
    try:
        title = event.get("summary", "Untitled Event")
        description = event.get("description", "") or ""
        location = event.get("location", "") or ""
        attendees = extract_attendees(event)
        
        # Build prompt
        system_prompt = """You are an expert at analyzing calendar events and extracting actionable task information.
Analyze the event details and extract:
1. Priority level (high, medium, low, or normal)
2. Whether it's critical (must-do, cannot be skipped)
3. Whether it's urgent (time-sensitive, needs immediate attention)
4. Any deadlines mentioned in the description
5. Task complexity (low, medium, or high) based on description, duration, and attendees

Return a JSON object with these fields."""
        
        user_prompt = f"""Event Title: {title}
Description: {description}
Location: {location}
Attendees: {', '.join(attendees) if attendees else 'None'}

Extract task information and return JSON with:
- extracted_priority: "high", "medium", "low", or "normal"
- is_critical: boolean
- is_urgent: boolean
- deadline: ISO datetime string if deadline mentioned, null otherwise
- task_complexity: "low", "medium", or "high"
- reasoning: brief explanation (max 50 words)"""
        
        StructuredLogger.log_event(
            "chatgpt_extraction_start",
            f"Starting ChatGPT extraction for event: {title}",
            user_id=user_id,
            metadata={"event_id": event.get("id", "unknown"), "title": title},
        )
        
        # Try gpt-4o first, fallback to gpt-3.5-turbo
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
        except Exception as e:
            StructuredLogger.log_event(
                "chatgpt_extraction_fallback",
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
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            except Exception as e2:
                StructuredLogger.log_event(
                    "chatgpt_extraction_failed",
                    f"ChatGPT extraction failed: {str(e2)}",
                    user_id=user_id,
                    metadata={"error": str(e2)},
                    level="WARNING"
                )
                return None
        
        # Parse response
        content = response.choices[0].message.content
        extraction_result = json.loads(content)
        
        StructuredLogger.log_event(
            "chatgpt_extraction_success",
            f"ChatGPT extraction completed for event: {title}",
            user_id=user_id,
            metadata={
                "event_id": event.get("id", "unknown"),
                "priority": extraction_result.get("extracted_priority"),
                "is_critical": extraction_result.get("is_critical"),
                "is_urgent": extraction_result.get("is_urgent"),
            },
        )
        
        return extraction_result
        
    except json.JSONDecodeError as e:
        StructuredLogger.log_event(
            "chatgpt_extraction_json_error",
            f"Failed to parse ChatGPT JSON response: {str(e)}",
            user_id=user_id,
            metadata={"error": str(e), "content": content[:200] if 'content' in locals() else "N/A"},
            level="WARNING"
        )
        return None
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": user_id,
                "event_id": event.get("id", "unknown"),
                "function": "extract_task_with_chatgpt"
            }
        )
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
        
        # Try ChatGPT extraction first
        chatgpt_result = extract_task_with_chatgpt(event, user_id)
        
        # Initialize with rule-based extraction as fallback
        extracted_priority = extract_priority_from_title(title)
        is_critical = False
        is_urgent = False
        
        # Merge ChatGPT results if available
        if chatgpt_result:
            # Use ChatGPT priority if available, otherwise fallback to rule-based
            if chatgpt_result.get("extracted_priority"):
                extracted_priority = chatgpt_result.get("extracted_priority")
            
            # Use ChatGPT critical/urgent flags
            is_critical = chatgpt_result.get("is_critical", False)
            is_urgent = chatgpt_result.get("is_urgent", False)
            
            # If ChatGPT didn't set critical/urgent but priority is high, infer them
            if extracted_priority == "high" and not is_critical and not is_urgent:
                # Check if rule-based would have marked it as high priority
                rule_based_priority = extract_priority_from_title(title)
                if rule_based_priority == "high":
                    is_urgent = True  # High priority from title usually means urgent
        else:
            # Fallback to rule-based: if title has urgent keywords, mark as urgent
            rule_based_priority = extract_priority_from_title(title)
            if rule_based_priority == "high":
                is_urgent = True
            # Check for critical keywords in title
            title_lower = title.lower()
            if any(keyword in title_lower for keyword in ['critical', 'must', 'required']):
                is_critical = True
        
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
            is_critical=is_critical,
            is_urgent=is_urgent,
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

