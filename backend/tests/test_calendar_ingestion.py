"""Tests for calendar ingestion"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.perception.calendar_ingestion import (
    fetch_calendar_events,
    CalendarIngestionError,
)


@pytest.mark.asyncio
async def test_fetch_calendar_events_no_credentials():
    """Test fetching events without credentials"""
    with patch('app.agents.perception.calendar_ingestion.get_user_credentials', return_value=None):
        with pytest.raises(CalendarIngestionError):
            await fetch_calendar_events("user-123")


@pytest.mark.asyncio
async def test_fetch_calendar_events_success():
    """Test successful event fetching"""
    mock_credentials = Mock()
    mock_service = Mock()
    mock_events = {
        'items': [
            {
                'id': 'event1',
                'summary': 'Test Event',
                'start': {'dateTime': '2024-01-15T10:00:00Z'},
                'end': {'dateTime': '2024-01-15T11:00:00Z'},
            }
        ]
    }
    
    mock_service.events.return_value.list.return_value.execute.return_value = mock_events
    
    with patch('app.agents.perception.calendar_ingestion.get_user_credentials', return_value=mock_credentials):
        with patch('app.agents.perception.calendar_ingestion.build', return_value=mock_service):
            events = await fetch_calendar_events("user-123")
            assert len(events) == 1
            assert events[0]['id'] == 'event1'

