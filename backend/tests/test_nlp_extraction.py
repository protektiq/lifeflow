"""Tests for NLP extraction logic"""
import pytest
from datetime import datetime
from app.agents.perception.nlp_extraction import (
    extract_priority_from_title,
    parse_datetime,
    extract_attendees,
    extract_raw_task_from_event,
)


def test_extract_priority_high():
    """Test high priority extraction"""
    assert extract_priority_from_title("URGENT: Meeting") == "high"
    assert extract_priority_from_title("Important call ASAP") == "high"
    assert extract_priority_from_title("Critical task!") == "high"


def test_extract_priority_medium():
    """Test medium priority extraction"""
    assert extract_priority_from_title("Team Meeting") == "medium"
    assert extract_priority_from_title("Client Call") == "medium"


def test_extract_priority_low():
    """Test low priority extraction"""
    assert extract_priority_from_title("Optional review") == "low"
    assert extract_priority_from_title("Tentative lunch") == "low"


def test_extract_priority_none():
    """Test no priority extraction"""
    assert extract_priority_from_title("Regular event") is None


def test_parse_datetime_all_day():
    """Test parsing all-day event datetime"""
    date_str = "2024-01-15"
    result = parse_datetime(date_str, is_all_day=True)
    assert result == datetime(2024, 1, 15)


def test_parse_datetime_with_time():
    """Test parsing datetime with time"""
    date_str = "2024-01-15T10:00:00Z"
    result = parse_datetime(date_str, is_all_day=False)
    assert isinstance(result, datetime)


def test_extract_attendees():
    """Test attendee extraction"""
    event = {
        "attendees": [
            {"email": "user1@example.com"},
            {"email": "user2@example.com"},
        ]
    }
    attendees = extract_attendees(event)
    assert len(attendees) == 2
    assert "user1@example.com" in attendees
    assert "user2@example.com" in attendees


def test_extract_attendees_empty():
    """Test attendee extraction with no attendees"""
    event = {}
    attendees = extract_attendees(event)
    assert attendees == []


def test_extract_raw_task_from_event():
    """Test full task extraction from event"""
    event = {
        "id": "test-event-123",
        "summary": "Team Meeting",
        "description": "Weekly sync",
        "location": "Conference Room A",
        "start": {
            "dateTime": "2024-01-15T10:00:00Z"
        },
        "end": {
            "dateTime": "2024-01-15T11:00:00Z"
        },
        "attendees": [
            {"email": "user1@example.com"},
        ],
        "status": "confirmed",
    }
    
    task = extract_raw_task_from_event(event, "user-123")
    
    assert task.title == "Team Meeting"
    assert task.description == "Weekly sync"
    assert task.location == "Conference Room A"
    assert len(task.attendees) == 1
    assert task.source == "google_calendar"
    assert task.extracted_priority == "medium"

