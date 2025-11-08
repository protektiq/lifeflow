"""Google Calendar API integration for event ingestion"""
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.database import supabase
from app.utils.monitoring import StructuredLogger, error_handler
import json

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class CalendarIngestionError(Exception):
    """Custom exception for calendar ingestion errors"""
    pass


@error_handler
async def get_user_credentials(user_id: str) -> Optional[Credentials]:
    """Retrieve and refresh user's Google OAuth credentials"""
    try:
        # Get stored OAuth tokens from database
        response = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", "google").execute()
        
        if not response.data:
            StructuredLogger.log_event(
                "oauth_token_not_found",
                f"No OAuth tokens found for user {user_id}",
                user_id=user_id,
                level="WARNING"
            )
            return None
        
        token_data = response.data[0]
        
        # Create credentials object
        credentials = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=SCOPES,
        )
        
        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            
            # Update stored token
            supabase.table("oauth_tokens").update({
                "access_token": credentials.token,
                "token_expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            }).eq("id", token_data["id"]).execute()
        
        return credentials
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "get_user_credentials"})
        raise CalendarIngestionError(f"Failed to retrieve credentials: {str(e)}")


@error_handler
async def fetch_calendar_events(
    user_id: str,
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 250
) -> List[Dict]:
    """Fetch calendar events from Google Calendar API"""
    credentials = await get_user_credentials(user_id)
    
    if not credentials:
        raise CalendarIngestionError("No valid credentials found. Please connect your Google Calendar.")
    
    try:
        # Build Calendar API service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Set default time range (last 30 days to next 90 days)
        if not time_min:
            time_min = datetime.utcnow() - timedelta(days=30)
        if not time_max:
            time_max = datetime.utcnow() + timedelta(days=90)
        
        # Fetch events
        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min.isoformat() + 'Z',
            timeMax=time_max.isoformat() + 'Z',
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        StructuredLogger.log_event(
            "calendar_events_fetched",
            f"Fetched {len(events)} events from Google Calendar",
            user_id=user_id,
            metadata={"event_count": len(events)},
        )
        
        return events
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "fetch_calendar_events"})
        raise CalendarIngestionError(f"Failed to fetch calendar events: {str(e)}")


@error_handler
async def store_oauth_tokens(
    user_id: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    expires_in: Optional[int] = None
):
    """Store OAuth tokens securely in database"""
    try:
        expires_at = None
        if expires_in:
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        # Check if tokens already exist
        existing = supabase.table("oauth_tokens").select("*").eq("user_id", user_id).eq("provider", "google").execute()
        
        token_data = {
            "user_id": user_id,
            "provider": "google",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_expires_at": expires_at,
            "scope": " ".join(SCOPES),
        }
        
        if existing.data:
            # Update existing tokens
            supabase.table("oauth_tokens").update(token_data).eq("id", existing.data[0]["id"]).execute()
        else:
            # Insert new tokens
            supabase.table("oauth_tokens").insert(token_data).execute()
        
        StructuredLogger.log_event(
            "oauth_tokens_stored",
            "OAuth tokens stored successfully",
            user_id=user_id,
        )
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "store_oauth_tokens"})
        raise CalendarIngestionError(f"Failed to store OAuth tokens: {str(e)}")

