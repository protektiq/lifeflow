"""Tests for LangGraph workflow"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.agents.orchestration.workflow import (
    auth_node,
    ingestion_node,
    extraction_node,
    storage_node,
    WorkflowState,
)


@pytest.mark.asyncio
async def test_auth_node_success():
    """Test successful authentication"""
    mock_credentials = Mock()
    mock_credentials.token = "test-token"
    
    state: WorkflowState = {
        "user_id": "user-123",
        "oauth_token": None,
        "calendar_events": [],
        "raw_tasks": [],
        "errors": [],
        "status": "started",
        "event_count": 0,
    }
    
    with patch('app.agents.orchestration.workflow.get_user_credentials', return_value=mock_credentials):
        result = await auth_node(state)
        assert result["status"] == "authenticated"
        assert result["oauth_token"] == "test-token"


@pytest.mark.asyncio
async def test_auth_node_no_credentials():
    """Test authentication failure"""
    state: WorkflowState = {
        "user_id": "user-123",
        "oauth_token": None,
        "calendar_events": [],
        "raw_tasks": [],
        "errors": [],
        "status": "started",
        "event_count": 0,
    }
    
    with patch('app.agents.orchestration.workflow.get_user_credentials', return_value=None):
        result = await auth_node(state)
        assert result["status"] == "error"
        assert len(result["errors"]) > 0

