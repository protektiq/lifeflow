"""Task Manager Integration - Base interface and Todoist implementation"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from app.database import supabase
from app.utils.monitoring import StructuredLogger, error_handler
import requests
from app.config import settings


class TaskManagerIntegrationError(Exception):
    """Custom exception for task manager integration errors"""
    pass


class TaskManagerIntegration(ABC):
    """Abstract base class for task manager integrations"""
    
    def __init__(self, provider: str):
        self.provider = provider
    
    @abstractmethod
    async def get_access_token(self, user_id: str) -> Optional[str]:
        """Get valid access token for user"""
        pass
    
    @abstractmethod
    async def fetch_tasks(self, user_id: str, **kwargs) -> List[Dict]:
        """Fetch tasks from external task manager"""
        pass
    
    @abstractmethod
    async def create_task(self, user_id: str, task_data: Dict) -> Dict:
        """Create a new task in external task manager"""
        pass
    
    @abstractmethod
    async def update_task(self, user_id: str, external_id: str, task_data: Dict) -> Dict:
        """Update an existing task in external task manager"""
        pass
    
    @abstractmethod
    async def delete_task(self, user_id: str, external_id: str) -> bool:
        """Delete a task from external task manager"""
        pass
    
    @abstractmethod
    def map_to_raw_task(self, external_task: Dict, user_id: str) -> Dict:
        """Map external task format to LifeFlow RawTask format"""
        pass
    
    @abstractmethod
    def map_from_raw_task(self, raw_task: Dict) -> Dict:
        """Map LifeFlow RawTask format to external task format"""
        pass


class TodoistIntegration(TaskManagerIntegration):
    """Todoist API integration"""
    
    API_BASE_URL = "https://api.todoist.com/rest/v2"
    OAUTH_BASE_URL = "https://todoist.com/oauth"
    
    def __init__(self):
        super().__init__("todoist")
    
    @error_handler
    async def get_access_token(self, user_id: str) -> Optional[str]:
        """Get valid Todoist access token for user"""
        try:
            # Get stored OAuth tokens from database
            response = supabase.table("oauth_tokens").select("*").eq(
                "user_id", user_id
            ).eq("provider", "todoist").execute()
            
            if not response.data:
                StructuredLogger.log_event(
                    "todoist_token_not_found",
                    f"No Todoist OAuth tokens found for user {user_id}",
                    user_id=user_id,
                    level="WARNING"
                )
                return None
            
            token_data = response.data[0]
            access_token = token_data["access_token"]
            
            # Todoist tokens don't expire, but check if we need to refresh
            # For now, just return the access token
            return access_token
        except Exception as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "get_access_token"})
            raise TaskManagerIntegrationError(f"Failed to retrieve Todoist credentials: {str(e)}")
    
    @error_handler
    async def fetch_tasks(self, user_id: str, **kwargs) -> List[Dict]:
        """Fetch tasks from Todoist API"""
        access_token = await self.get_access_token(user_id)
        
        if not access_token:
            raise TaskManagerIntegrationError("No valid Todoist credentials found. Please connect your Todoist account.")
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Fetch active tasks
            response = requests.get(
                f"{self.API_BASE_URL}/tasks",
                headers=headers,
                params={"filter": kwargs.get("filter", "all")},
                timeout=30
            )
            
            if response.status_code == 401:
                raise TaskManagerIntegrationError("Todoist authentication failed. Please reconnect your account.")
            
            response.raise_for_status()
            tasks = response.json()
            
            StructuredLogger.log_event(
                "todoist_tasks_fetched",
                f"Fetched {len(tasks)} tasks from Todoist",
                user_id=user_id,
                metadata={"task_count": len(tasks)},
            )
            
            return tasks
        except requests.exceptions.RequestException as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "fetch_tasks"})
            raise TaskManagerIntegrationError(f"Failed to fetch Todoist tasks: {str(e)}")
    
    @error_handler
    async def create_task(self, user_id: str, task_data: Dict) -> Dict:
        """Create a new task in Todoist"""
        access_token = await self.get_access_token(user_id)
        
        if not access_token:
            raise TaskManagerIntegrationError("No valid Todoist credentials found.")
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                f"{self.API_BASE_URL}/tasks",
                headers=headers,
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 401:
                raise TaskManagerIntegrationError("Todoist authentication failed.")
            
            response.raise_for_status()
            created_task = response.json()
            
            StructuredLogger.log_event(
                "todoist_task_created",
                f"Created task in Todoist: {task_data.get('content', 'Unknown')}",
                user_id=user_id,
                metadata={"task_id": created_task.get("id")},
            )
            
            return created_task
        except requests.exceptions.RequestException as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "create_task"})
            raise TaskManagerIntegrationError(f"Failed to create Todoist task: {str(e)}")
    
    @error_handler
    async def update_task(self, user_id: str, external_id: str, task_data: Dict) -> Dict:
        """Update an existing task in Todoist"""
        access_token = await self.get_access_token(user_id)
        
        if not access_token:
            raise TaskManagerIntegrationError("No valid Todoist credentials found.")
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            response = requests.post(
                f"{self.API_BASE_URL}/tasks/{external_id}",
                headers=headers,
                json=task_data,
                timeout=30
            )
            
            if response.status_code == 401:
                raise TaskManagerIntegrationError("Todoist authentication failed.")
            
            response.raise_for_status()
            updated_task = response.json()
            
            StructuredLogger.log_event(
                "todoist_task_updated",
                f"Updated task in Todoist: {external_id}",
                user_id=user_id,
                metadata={"task_id": external_id},
            )
            
            return updated_task
        except requests.exceptions.RequestException as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "update_task"})
            raise TaskManagerIntegrationError(f"Failed to update Todoist task: {str(e)}")
    
    @error_handler
    async def delete_task(self, user_id: str, external_id: str) -> bool:
        """Delete a task from Todoist"""
        access_token = await self.get_access_token(user_id)
        
        if not access_token:
            raise TaskManagerIntegrationError("No valid Todoist credentials found.")
        
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
            }
            
            response = requests.delete(
                f"{self.API_BASE_URL}/tasks/{external_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 401:
                raise TaskManagerIntegrationError("Todoist authentication failed.")
            
            response.raise_for_status()
            
            StructuredLogger.log_event(
                "todoist_task_deleted",
                f"Deleted task from Todoist: {external_id}",
                user_id=user_id,
                metadata={"task_id": external_id},
            )
            
            return True
        except requests.exceptions.RequestException as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "delete_task"})
            raise TaskManagerIntegrationError(f"Failed to delete Todoist task: {str(e)}")
    
    def map_to_raw_task(self, external_task: Dict, user_id: str) -> Dict:
        """Map Todoist task to LifeFlow RawTask format"""
        # Extract due date/time
        due = external_task.get("due", {})
        due_date_str = due.get("date") if due else None
        
        # Parse due date
        start_time = datetime.utcnow()
        end_time = datetime.utcnow() + timedelta(hours=1)
        
        if due_date_str:
            try:
                # Todoist dates can be in format "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SS"
                if "T" in due_date_str:
                    start_time = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
                else:
                    start_time = datetime.fromisoformat(f"{due_date_str}T09:00:00+00:00")
                
                # End time is 1 hour after start, or end of day for all-day tasks
                if due.get("is_recurring") or not due.get("datetime"):
                    end_time = datetime.fromisoformat(f"{due_date_str}T17:00:00+00:00")
                else:
                    end_time = start_time + timedelta(hours=1)
            except (ValueError, TypeError):
                # If parsing fails, use defaults
                pass
        
        # Map priority (Todoist: 1-4, LifeFlow: low/medium/high)
        priority_map = {1: "low", 2: "medium", 3: "high", 4: "high"}
        priority = priority_map.get(external_task.get("priority", 1), "medium")
        
        # Determine if critical/urgent based on priority
        is_critical = external_task.get("priority", 1) >= 3
        is_urgent = external_task.get("priority", 1) >= 4
        
        return {
            "source": "todoist",
            "title": external_task.get("content", "Untitled Task"),
            "description": external_task.get("description", ""),
            "start_time": start_time,
            "end_time": end_time,
            "attendees": [],
            "location": None,
            "recurrence_pattern": None,
            "extracted_priority": priority,
            "is_critical": is_critical,
            "is_urgent": is_urgent,
            "is_spam": False,
            "spam_reason": None,
            "spam_score": None,
            "raw_data": external_task,
            "external_id": str(external_task.get("id")),
            "sync_status": "synced",
            "sync_direction": "bidirectional",
            "external_updated_at": datetime.fromisoformat(external_task.get("updated_at", datetime.utcnow().isoformat())),
        }
    
    def map_from_raw_task(self, raw_task: Dict) -> Dict:
        """Map LifeFlow RawTask format to Todoist task format"""
        task_data = {
            "content": raw_task.get("title", "Untitled Task"),
        }
        
        # Add description if available
        if raw_task.get("description"):
            task_data["description"] = raw_task["description"]
        
        # Map priority (LifeFlow: low/medium/high, Todoist: 1-4)
        priority_map = {"low": 1, "medium": 2, "high": 3}
        priority = priority_map.get(raw_task.get("extracted_priority", "medium"), 2)
        
        # Boost priority if critical/urgent
        if raw_task.get("is_critical"):
            priority = max(priority, 3)
        if raw_task.get("is_urgent"):
            priority = 4
        
        task_data["priority"] = priority
        
        # Add due date if available
        start_time = raw_task.get("start_time")
        if start_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            
            # Format as ISO date string for Todoist
            task_data["due_string"] = start_time.strftime("%Y-%m-%d")
            if start_time.hour != 0 or start_time.minute != 0:
                task_data["due_datetime"] = start_time.isoformat()
        
        return task_data


async def store_todoist_tokens(
    user_id: str,
    access_token: str,
    expires_in: Optional[int] = None
):
    """Store Todoist OAuth tokens securely in database"""
    try:
        expires_at = None
        if expires_in:
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()
        
        # Check if tokens already exist
        existing = supabase.table("oauth_tokens").select("*").eq(
            "user_id", user_id
        ).eq("provider", "todoist").execute()
        
        token_data = {
            "user_id": user_id,
            "provider": "todoist",
            "access_token": access_token,
            "refresh_token": None,  # Todoist doesn't use refresh tokens
            "token_expires_at": expires_at,
            "scope": "task:add,data:read_write,data:delete",
        }
        
        if existing.data:
            # Update existing tokens
            supabase.table("oauth_tokens").update(token_data).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            # Insert new tokens
            supabase.table("oauth_tokens").insert(token_data).execute()
        
        StructuredLogger.log_event(
            "todoist_tokens_stored",
            "Todoist OAuth tokens stored successfully",
            user_id=user_id,
        )
    except Exception as e:
        StructuredLogger.log_error(e, context={"user_id": user_id, "function": "store_todoist_tokens"})
        raise TaskManagerIntegrationError(f"Failed to store Todoist OAuth tokens: {str(e)}")

