"""Gmail API integration for email ingestion"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.database import supabase
from app.utils.monitoring import StructuredLogger, error_handler
from app.agents.perception.calendar_ingestion import get_user_credentials
import base64
from email.utils import parsedate_to_datetime
import re

# Gmail API scopes
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class EmailIngestionError(Exception):
    """Custom exception for email ingestion errors"""
    pass


@error_handler
async def get_user_gmail_credentials(user_id: str) -> Optional[Credentials]:
    """Retrieve and refresh user's Google OAuth credentials for Gmail API"""
    # Reuse the same credentials function from calendar_ingestion
    # The credentials will have both Calendar and Gmail scopes
    return await get_user_credentials(user_id)


@error_handler
def parse_email_message(message_data: Dict) -> Dict:
    """
    Parse Gmail API message data into structured format
    
    Args:
        message_data: Raw message data from Gmail API
        
    Returns:
        Dictionary with parsed email fields:
        - id: Message ID
        - thread_id: Thread ID
        - subject: Email subject
        - sender: Sender email address
        - date: Email date (datetime)
        - body_text: Plain text body
        - body_html: HTML body (if available)
        - snippet: Email snippet
        - labels: List of labels (including UNREAD, STARRED/FLAGGED)
    """
    try:
        headers = message_data.get('payload', {}).get('headers', [])
        
        # Extract headers
        subject = ""
        sender = ""
        date_str = ""
        
        for header in headers:
            name = header.get('name', '').lower()
            value = header.get('value', '')
            
            if name == 'subject':
                subject = value
            elif name == 'from':
                sender = value
            elif name == 'date':
                date_str = value
        
        # Parse date
        email_date = None
        if date_str:
            try:
                email_date = parsedate_to_datetime(date_str)
            except Exception:
                # Fallback to current time if parsing fails
                email_date = datetime.utcnow()
        else:
            email_date = datetime.utcnow()
        
        # Extract body
        body_text = ""
        body_html = ""
        
        payload = message_data.get('payload', {})
        
        def extract_body(part: Dict, text_parts: List[str], html_parts: List[str]):
            """Recursively extract body from message parts"""
            mime_type = part.get('mimeType', '')
            body_data = part.get('body', {}).get('data', '')
            
            if body_data:
                try:
                    decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    if mime_type == 'text/plain':
                        text_parts.append(decoded_body)
                    elif mime_type == 'text/html':
                        html_parts.append(decoded_body)
                except Exception:
                    pass
            
            # Check for multipart messages
            parts = part.get('parts', [])
            for subpart in parts:
                extract_body(subpart, text_parts, html_parts)
        
        text_parts = []
        html_parts = []
        
        if payload.get('mimeType', '').startswith('multipart/'):
            parts = payload.get('parts', [])
            for part in parts:
                extract_body(part, text_parts, html_parts)
        else:
            # Single part message
            extract_body(payload, text_parts, html_parts)
        
        body_text = '\n'.join(text_parts)
        body_html = '\n'.join(html_parts)
        
        # If no plain text but HTML exists, extract text from HTML
        if not body_text and body_html:
            # Simple HTML tag removal (basic implementation)
            body_text = re.sub(r'<[^>]+>', '', body_html)
            body_text = re.sub(r'\s+', ' ', body_text).strip()
        
        # Extract labels
        labels = message_data.get('labelIds', [])
        
        return {
            'id': message_data.get('id', ''),
            'thread_id': message_data.get('threadId', ''),
            'subject': subject,
            'sender': sender,
            'date': email_date,
            'body_text': body_text,
            'body_html': body_html,
            'snippet': message_data.get('snippet', ''),
            'labels': labels,
            'raw_data': message_data,  # Store full raw data
        }
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={
                "message_id": message_data.get('id', 'unknown'),
                "function": "parse_email_message"
            }
        )
        raise EmailIngestionError(f"Failed to parse email message: {str(e)}")


@error_handler
async def fetch_gmail_messages(
    user_id: str,
    query: str = 'is:unread OR is:flagged -is:spam',
    max_results: int = 50
) -> List[Dict]:
    """
    Fetch emails from Gmail API
    
    Args:
        user_id: User ID
        query: Gmail search query (default: unread or flagged emails)
        max_results: Maximum number of messages to fetch
        
    Returns:
        List of parsed email message dictionaries
    """
    credentials = await get_user_gmail_credentials(user_id)
    
    if not credentials:
        raise EmailIngestionError("No valid credentials found. Please connect your Google account.")
    
    try:
        # Build Gmail API service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Add date restriction: only fetch emails from last 30 days
        # Gmail query format: after:YYYY/MM/DD
        date_30_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime('%Y/%m/%d')
        date_query = f'after:{date_30_days_ago}'
        
        # Combine user query with date restriction
        if query:
            full_query = f'({query}) {date_query}'
        else:
            full_query = date_query
        
        StructuredLogger.log_event(
            "gmail_query_with_date_restriction",
            f"Fetching emails with date restriction: {full_query}",
            user_id=user_id,
            metadata={"date_30_days_ago": date_30_days_ago, "original_query": query},
        )
        
        # List messages matching query
        messages_result = service.users().messages().list(
            userId='me',
            q=full_query,
            maxResults=max_results
        ).execute()
        
        messages = messages_result.get('messages', [])
        
        StructuredLogger.log_event(
            "gmail_messages_listed",
            f"Found {len(messages)} messages matching query: {query}",
            user_id=user_id,
            metadata={"message_count": len(messages), "query": query},
        )
        
        # Fetch full message details
        parsed_messages = []
        for message in messages:
            try:
                message_id = message['id']
                message_detail = service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='full'
                ).execute()
                
                parsed_message = parse_email_message(message_detail)
                parsed_messages.append(parsed_message)
                
            except Exception as e:
                StructuredLogger.log_event(
                    "gmail_message_fetch_error",
                    f"Failed to fetch message {message.get('id', 'unknown')}",
                    user_id=user_id,
                    metadata={"error": str(e), "message_id": message.get('id', 'unknown')},
                    level="WARNING"
                )
                continue
        
        StructuredLogger.log_event(
            "gmail_messages_fetched",
            f"Fetched {len(parsed_messages)} email messages from Gmail",
            user_id=user_id,
            metadata={"message_count": len(parsed_messages)},
        )
        
        return parsed_messages
        
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "fetch_gmail_messages"})
        raise EmailIngestionError(f"Failed to fetch Gmail messages: {str(e)}")

