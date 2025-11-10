"""NLP extraction logic to parse calendar events and emails into RawTask objects"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
from openai import OpenAI
from app.config import settings
from app.models.task import RawTaskCreate
from app.utils.monitoring import StructuredLogger, error_handler
from app.agents.perception.spam_filter import detect_spam
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


def extract_due_date_from_text(text: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Extract due date from text using regex patterns and NLP
    
    Args:
        text: Text to search for dates
        reference_date: Reference date for relative dates (defaults to now)
        
    Returns:
        Parsed datetime if found, None otherwise
    """
    if not text:
        return None
    
    if reference_date is None:
        reference_date = datetime.utcnow()
    
    # Common date patterns
    patterns = [
        # "Due by [date]", "Due [date]", "Deadline: [date]"
        (r'due\s+(?:by|on|before)?\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
        (r'deadline\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
        # "By [date]", "Before [date]"
        (r'(?:by|before)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', re.IGNORECASE),
        # Relative dates: "due tomorrow", "due next week", "due in 3 days"
        (r'due\s+(?:in\s+)?(\d+)\s+(?:day|days)', re.IGNORECASE),
        (r'due\s+(?:in\s+)?(\d+)\s+(?:week|weeks)', re.IGNORECASE),
        (r'due\s+(?:in\s+)?(\d+)\s+(?:month|months)', re.IGNORECASE),
        (r'due\s+tomorrow', re.IGNORECASE),
        (r'due\s+next\s+week', re.IGNORECASE),
        # ISO dates: "2024-12-31", "2024/12/31"
        (r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', re.IGNORECASE),
        # Month day: "December 31", "Dec 31", "12/31"
        (r'(\w+\s+\d{1,2}(?:st|nd|rd|th)?)', re.IGNORECASE),
    ]
    
    for pattern, flags in patterns:
        matches = re.finditer(pattern, text, flags)
        for match in matches:
            try:
                date_str = match.group(1) if match.groups() else match.group(0)
                
                # Handle relative dates
                if 'tomorrow' in match.group(0).lower():
                    return reference_date + timedelta(days=1)
                elif 'next week' in match.group(0).lower():
                    return reference_date + timedelta(weeks=1)
                elif 'day' in match.group(0).lower() or 'days' in match.group(0).lower():
                    days = int(match.group(1))
                    return reference_date + timedelta(days=days)
                elif 'week' in match.group(0).lower() or 'weeks' in match.group(0).lower():
                    weeks = int(match.group(1))
                    return reference_date + timedelta(weeks=weeks)
                elif 'month' in match.group(0).lower() or 'months' in match.group(0).lower():
                    months = int(match.group(1))
                    return reference_date + relativedelta(months=months)
                
                # Try parsing the date string
                parsed_date = date_parser.parse(date_str, default=reference_date)
                return parsed_date
            except Exception:
                continue
    
    return None


def extract_task_with_chatgpt_from_email(email_data: Dict, user_id: str, spam_detection: Optional[Dict[str, Any]] = None) -> Optional[Dict]:
    """
    Extract task information from email using ChatGPT
    
    Args:
        email_data: Email message dictionary with subject, sender, body_text, etc.
        user_id: User ID for logging
        spam_detection: Optional spam detection results from rule-based filter
        
    Returns:
        Dictionary with extracted fields or None if extraction fails:
        - extracted_priority: "high", "medium", "low", or "normal"
        - is_critical: boolean
        - is_urgent: boolean
        - deadline: ISO datetime string if mentioned in email
        - has_task: boolean (whether email contains actionable task/commitment)
        - task_description: extracted task description
        - is_spam: boolean (whether email is spam/promotional)
        - reasoning: brief explanation of extraction decisions
    """
    try:
        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body_text = email_data.get("body_text", "")
        snippet = email_data.get("snippet", "")
        labels = email_data.get("labels", [])
        
        # Check if email is flagged/starred
        is_flagged = "STARRED" in labels or "FLAGGED" in labels
        
        # Build prompt with spam detection context
        system_prompt = """You are an expert at analyzing emails and extracting actionable tasks and commitments.
Analyze the email and extract:
1. Whether the email contains an actionable task or commitment (not just informational)
2. Whether the email is spam, promotional, or marketing content
3. Priority level (high, medium, low, or normal) based on urgency language and sender
4. Whether it's critical (must-do, cannot be skipped)
5. Whether it's urgent (time-sensitive, needs immediate attention)
6. Any deadlines or due dates mentioned in the email body
7. A clear task description if a task/commitment is identified

Focus on explicit commitments like "I will...", "I'll complete...", "Please do...", "Action required:", etc.
Ignore purely informational emails, newsletters, or emails without clear action items.

IMPORTANT SPAM DETECTION GUIDELINES:
- Mark as spam ONLY if the email is clearly promotional (sales offers, product promotions, newsletters, marketing campaigns)
- DO NOT mark as spam if the email mentions work-related departments (e.g., "marketing department", "sales management", "product management") in a legitimate work context
- Legitimate work tasks that mention coordinating with teams/departments are NOT spam
- Examples of spam: "Buy now", "Special offer", "Activate your deal", "Review this product to purchase"
- Examples of NOT spam: "Build a proposal deck after coordinating with marketing", "Follow up with sales management", "Review proposal"

If the email is promotional/spam, mark is_spam as true and set priority to "low". Otherwise, assign appropriate priority based on urgency and importance.

Return a JSON object with these fields."""
        
        # Truncate body if too long (keep first 2000 chars for context)
        body_preview = body_text[:2000] if len(body_text) > 2000 else body_text
        
        # Log body availability for debugging
        if not body_text or len(body_text.strip()) == 0:
            StructuredLogger.log_event(
                "email_body_empty",
                f"Email body is empty for: {subject}",
                user_id=user_id,
                metadata={
                    "message_id": email_data.get("id", "unknown"),
                    "sender": sender,
                    "has_snippet": bool(email_data.get("snippet")),
                },
                level="WARNING"
            )
        
        # Include spam detection results in prompt if available
        spam_context = ""
        if spam_detection:
            is_spam_rule = spam_detection.get('is_spam', False)
            spam_reason_rule = spam_detection.get('spam_reason', 'None')
            spam_score_rule = spam_detection.get('spam_score', 0.0)
            
            spam_context = f"""
Rule-based Spam Detection Results:
- Is Spam: {is_spam_rule}
- Spam Reason: {spam_reason_rule}
- Spam Score: {spam_score_rule}

IMPORTANT: Please carefully validate this spam detection. If the email is a legitimate work task (even if it mentions departments like "marketing" or "sales"), it is NOT spam. Only mark as spam if it's clearly promotional content (sales offers, product promotions, newsletters). If spam is detected (by rules or your analysis), set priority to "low". Otherwise, assign normal priority based on task importance."""
        
        user_prompt = f"""Email Subject: {subject}
From: {sender}
Flagged/Starred: {is_flagged}
{spam_context}
Email Body:
{body_preview}

Extract task information and return JSON with:
- has_task: boolean (true if email contains actionable task/commitment)
- task_description: string (clear description of the task, null if no task)
- is_spam: boolean (true if email is promotional/spam)
- extracted_priority: "high", "medium", "low", or "normal" (null if no task, "low" if spam)
- is_critical: boolean
- is_urgent: boolean
- deadline: ISO datetime string if deadline mentioned, null otherwise
- reasoning: brief explanation (max 50 words)"""
        
        StructuredLogger.log_event(
            "chatgpt_email_extraction_start",
            f"Starting ChatGPT extraction for email: {subject}",
            user_id=user_id,
            metadata={"message_id": email_data.get("id", "unknown"), "subject": subject},
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
                "chatgpt_email_extraction_fallback",
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
                    "chatgpt_email_extraction_failed",
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
            "chatgpt_email_extraction_success",
            f"ChatGPT extraction completed for email: {subject}",
            user_id=user_id,
            metadata={
                "message_id": email_data.get("id", "unknown"),
                "has_task": extraction_result.get("has_task"),
                "priority": extraction_result.get("extracted_priority"),
            },
        )
        
        return extraction_result
        
    except json.JSONDecodeError as e:
        StructuredLogger.log_event(
            "chatgpt_email_extraction_json_error",
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
                "message_id": email_data.get("id", "unknown"),
                "function": "extract_task_with_chatgpt_from_email"
            }
        )
        return None


@error_handler
def extract_raw_task_from_email(email_data: Dict, user_id: str) -> Optional[RawTaskCreate]:
    """
    Extract RawTask from email message
    
    Args:
        email_data: Parsed email message dictionary
        user_id: User ID for logging
        
    Returns:
        RawTaskCreate if task/commitment found, None otherwise
    """
    try:
        subject = email_data.get("subject", "")
        sender = email_data.get("sender", "")
        body_text = email_data.get("body_text", "")
        email_date = email_data.get("date", datetime.utcnow())
        labels = email_data.get("labels", [])
        
        # Perform spam detection BEFORE ChatGPT analysis
        spam_detection = detect_spam(email_data)
        is_spam_rule_based = spam_detection.get("is_spam", False)
        spam_reason = spam_detection.get("spam_reason")
        spam_score = spam_detection.get("spam_score", 0.0)
        
        # Log spam detection with body preview for debugging
        body_preview_for_log = body_text[:200] if body_text else "(empty)"
        StructuredLogger.log_event(
            "spam_detection_result",
            f"Spam detection for email: {subject}",
            user_id=user_id,
            metadata={
                "message_id": email_data.get("id", "unknown"),
                "is_spam": is_spam_rule_based,
                "spam_reason": spam_reason,
                "spam_score": spam_score,
                "sender": sender,
                "subject": subject,
                "body_length": len(body_text) if body_text else 0,
                "body_preview": body_preview_for_log,
            },
        )
        
        # Use ChatGPT to extract task information (pass spam detection results)
        chatgpt_result = extract_task_with_chatgpt_from_email(email_data, user_id, spam_detection=spam_detection)
        
        # If ChatGPT says no task, skip this email
        if not chatgpt_result or not chatgpt_result.get("has_task", False):
            return None
        
        # Extract spam detection from ChatGPT (hybrid approach)
        is_spam_ai = chatgpt_result.get("is_spam", False)
        
        # Trust ChatGPT's judgment for nuanced cases (it understands context better)
        # Only override ChatGPT if rule-based detection has very high confidence (Gmail SPAM label)
        # Rule-based detection spam_score of 1.0 means Gmail explicitly marked it as SPAM
        gmail_explicit_spam = is_spam_rule_based and spam_score >= 1.0
        
        if gmail_explicit_spam:
            # Gmail explicitly marked as SPAM - trust that over ChatGPT
            is_spam = True
            spam_reason = spam_reason or "Gmail SPAM label"
        elif is_spam_ai:
            # ChatGPT detected spam
            is_spam = True
            spam_reason = f"AI detected spam; {spam_reason}" if spam_reason else "AI detected spam"
            spam_score = max(spam_score, 0.6)  # Boost score if AI confirms
        else:
            # ChatGPT says NOT spam - trust its judgment (it understands context)
            is_spam = False
            spam_reason = None
            spam_score = 0.0
        
        # Extract task description (use ChatGPT result or fallback to subject)
        task_description = chatgpt_result.get("task_description")
        if not task_description:
            task_description = subject
        
        # Extract due date
        deadline_str = chatgpt_result.get("deadline")
        due_date = None
        
        if deadline_str:
            try:
                due_date = date_parser.parse(deadline_str)
            except Exception:
                pass
        
        # If no deadline from ChatGPT, try regex extraction
        if not due_date:
            due_date = extract_due_date_from_text(body_text, reference_date=email_date)
        
        # Set start_time and end_time
        # For emails, start_time is email date, end_time is due_date if available
        start_time = email_date
        end_time = due_date if due_date else (email_date + timedelta(days=7))  # Default 7 days if no due date
        
        # Extract priority from ChatGPT
        extracted_priority = chatgpt_result.get("extracted_priority")
        
        # IMPORTANT: Only force priority to "low" if spam is detected
        # If ChatGPT says NOT spam, trust its priority assignment (it understands context)
        if is_spam:
            extracted_priority = "low"
            StructuredLogger.log_event(
                "spam_priority_forced",
                f"Spam detected, forcing priority to 'low' for email: {subject}",
                user_id=user_id,
                metadata={
                    "message_id": email_data.get("id", "unknown"),
                    "spam_reason": spam_reason,
                    "spam_score": spam_score,
                    "chatgpt_priority": chatgpt_result.get("extracted_priority"),
                    "chatgpt_is_spam": chatgpt_result.get("is_spam"),
                },
            )
        elif not extracted_priority:
            # Fallback to rule-based priority only if not spam and ChatGPT didn't provide priority
            extracted_priority = extract_priority_from_title(subject)
        else:
            # ChatGPT provided priority and it's not spam - log it for debugging
            StructuredLogger.log_event(
                "priority_assigned_by_chatgpt",
                f"Priority assigned by ChatGPT: {extracted_priority}",
                user_id=user_id,
                metadata={
                    "message_id": email_data.get("id", "unknown"),
                    "subject": subject,
                    "extracted_priority": extracted_priority,
                    "chatgpt_is_spam": chatgpt_result.get("is_spam"),
                    "chatgpt_reasoning": chatgpt_result.get("reasoning"),
                },
            )
        
        # Extract critical/urgent flags
        is_critical = chatgpt_result.get("is_critical", False)
        is_urgent = chatgpt_result.get("is_urgent", False)
        
        # If spam, don't mark as critical or urgent
        if is_spam:
            is_critical = False
            is_urgent = False
        
        # If flagged/starred, increase priority (unless spam)
        is_flagged = "STARRED" in labels or "FLAGGED" in labels
        if is_flagged and not is_urgent and not is_spam:
            is_urgent = True
            if not extracted_priority or extracted_priority == "normal":
                extracted_priority = "high"
        
        # Extract sender email from "Name <email>" format
        sender_email = sender
        if "<" in sender and ">" in sender:
            match = re.search(r'<([^>]+)>', sender)
            if match:
                sender_email = match.group(1)
        
        return RawTaskCreate(
            source="gmail",
            title=task_description or subject,
            description=f"From: {sender}\n\n{body_text[:500]}..." if len(body_text) > 500 else f"From: {sender}\n\n{body_text}",
            start_time=start_time,
            end_time=end_time,
            attendees=[sender_email] if sender_email else [],
            location=None,
            recurrence_pattern=None,
            extracted_priority=extracted_priority,
            is_critical=is_critical,
            is_urgent=is_urgent,
            is_spam=is_spam,
            spam_reason=spam_reason,
            spam_score=spam_score,
            raw_data=email_data.get("raw_data", {}) or {"id": email_data.get("id")},
        )
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "user_id": user_id,
                "message_id": email_data.get("id", "unknown"),
                "function": "extract_raw_task_from_email"
            }
        )
        raise NLPExtractionError(f"Failed to extract task from email: {str(e)}")


@error_handler
def extract_raw_tasks_from_emails(emails: List[Dict], user_id: str) -> List[RawTaskCreate]:
    """
    Extract multiple RawTasks from a list of emails
    
    Args:
        emails: List of parsed email message dictionaries
        user_id: User ID for logging
        
    Returns:
        List of RawTaskCreate objects (only emails with actionable tasks)
    """
    raw_tasks = []
    errors = []
    skipped_count = 0
    
    for email_data in emails:
        try:
            raw_task = extract_raw_task_from_email(email_data, user_id)
            
            if raw_task:
                raw_tasks.append(raw_task)
            else:
                skipped_count += 1
                
        except Exception as e:
            errors.append({
                "message_id": email_data.get("id", "unknown"),
                "error": str(e),
            })
            StructuredLogger.log_event(
                "email_task_extraction_error",
                f"Failed to extract task from email {email_data.get('id', 'unknown')}",
                user_id=user_id,
                metadata={"error": str(e)},
                level="WARNING"
            )
    
    StructuredLogger.log_event(
        "email_extraction_summary",
        f"Extracted {len(raw_tasks)} tasks from {len(emails)} emails ({skipped_count} skipped, {len(errors)} errors)",
        user_id=user_id,
        metadata={
            "success_count": len(raw_tasks),
            "skipped_count": skipped_count,
            "error_count": len(errors),
            "total_emails": len(emails)
        },
    )
    
    return raw_tasks

