"""Task Manager Sync Service - Bidirectional sync logic"""
from typing import List, Dict, Optional
from datetime import datetime, timezone
from app.database import supabase
from app.agents.perception.task_manager_integration import TodoistIntegration, TaskManagerIntegrationError
from app.models.task import RawTaskCreate
from app.utils.monitoring import StructuredLogger, error_handler
from uuid import UUID


class TaskSyncService:
    """Service for managing bidirectional sync with task managers"""
    
    def __init__(self):
        self.integrations = {
            "todoist": TodoistIntegration(),
        }
    
    @error_handler
    async def sync_tasks_inbound(
        self,
        user_id: str,
        provider: str = "todoist"
    ) -> Dict:
        """Pull tasks from external task manager and sync to LifeFlow"""
        if provider not in self.integrations:
            raise TaskManagerIntegrationError(f"Unsupported provider: {provider}")
        
        integration = self.integrations[provider]
        
        try:
            StructuredLogger.log_event(
                "sync_inbound_start",
                f"Starting inbound sync from {provider}",
                user_id=user_id,
            )
            
            # Fetch tasks from external provider
            external_tasks = await integration.fetch_tasks(user_id)
            
            synced_count = 0
            updated_count = 0
            created_count = 0
            conflicts = []
            errors = []
            
            for external_task in external_tasks:
                try:
                    # Map to RawTask format
                    mapped_task = integration.map_to_raw_task(external_task, user_id)
                    external_id = mapped_task.get("external_id")
                    external_updated_at = mapped_task.get("external_updated_at")
                    
                    if not external_id:
                        continue
                    
                    # Check if task already exists
                    existing_response = supabase.table("raw_tasks").select("*").eq(
                        "user_id", user_id
                    ).eq("source", provider).eq("external_id", external_id).execute()
                    
                    if existing_response.data:
                        # Task exists - check for conflicts
                        existing_task = existing_response.data[0]
                        existing_updated_at = existing_task.get("updated_at")
                        existing_external_updated_at = existing_task.get("external_updated_at")
                        
                        # Check if external task was updated more recently
                        if external_updated_at and existing_external_updated_at:
                            try:
                                ext_time = datetime.fromisoformat(
                                    external_updated_at.replace("Z", "+00:00")
                                ) if isinstance(external_updated_at, str) else external_updated_at
                                existing_ext_time = datetime.fromisoformat(
                                    existing_external_updated_at.replace("Z", "+00:00")
                                ) if isinstance(existing_external_updated_at, str) else existing_external_updated_at
                                
                                if ext_time > existing_ext_time:
                                    # External is newer - check if local was modified
                                    local_updated_at = datetime.fromisoformat(
                                        existing_updated_at.replace("Z", "+00:00")
                                    ) if isinstance(existing_updated_at, str) else existing_updated_at
                                    
                                    if local_updated_at > existing_ext_time:
                                        # Conflict: both were modified
                                        conflicts.append({
                                            "task_id": existing_task["id"],
                                            "external_id": external_id,
                                            "local_title": existing_task.get("title"),
                                            "external_title": mapped_task.get("title"),
                                        })
                                        # Mark as conflict
                                        supabase.table("raw_tasks").update({
                                            "sync_status": "conflict",
                                            "sync_error": "Both local and external tasks were modified",
                                        }).eq("id", existing_task["id"]).execute()
                                        continue
                            except (ValueError, TypeError):
                                pass
                        
                        # Update existing task
                        update_data = {
                            "title": mapped_task.get("title"),
                            "description": mapped_task.get("description"),
                            "start_time": mapped_task.get("start_time").isoformat() if isinstance(mapped_task.get("start_time"), datetime) else mapped_task.get("start_time"),
                            "end_time": mapped_task.get("end_time").isoformat() if isinstance(mapped_task.get("end_time"), datetime) else mapped_task.get("end_time"),
                            "extracted_priority": mapped_task.get("extracted_priority"),
                            "is_critical": mapped_task.get("is_critical", False),
                            "is_urgent": mapped_task.get("is_urgent", False),
                            "raw_data": mapped_task.get("raw_data", {}),
                            "external_updated_at": external_updated_at.isoformat() if isinstance(external_updated_at, datetime) else external_updated_at,
                            "sync_status": "synced",
                            "last_synced_at": datetime.utcnow().isoformat(),
                            "sync_error": None,
                        }
                        
                        supabase.table("raw_tasks").update(update_data).eq(
                            "id", existing_task["id"]
                        ).execute()
                        
                        updated_count += 1
                    else:
                        # Create new task
                        task_data = {
                            "user_id": user_id,
                            "source": provider,
                            "title": mapped_task.get("title"),
                            "description": mapped_task.get("description"),
                            "start_time": mapped_task.get("start_time").isoformat() if isinstance(mapped_task.get("start_time"), datetime) else mapped_task.get("start_time"),
                            "end_time": mapped_task.get("end_time").isoformat() if isinstance(mapped_task.get("end_time"), datetime) else mapped_task.get("end_time"),
                            "attendees": mapped_task.get("attendees", []),
                            "location": mapped_task.get("location"),
                            "recurrence_pattern": mapped_task.get("recurrence_pattern"),
                            "extracted_priority": mapped_task.get("extracted_priority"),
                            "is_critical": mapped_task.get("is_critical", False),
                            "is_urgent": mapped_task.get("is_urgent", False),
                            "is_spam": mapped_task.get("is_spam", False),
                            "spam_reason": mapped_task.get("spam_reason"),
                            "spam_score": mapped_task.get("spam_score"),
                            "raw_data": mapped_task.get("raw_data", {}),
                            "external_id": external_id,
                            "sync_status": "synced",
                            "sync_direction": mapped_task.get("sync_direction", "bidirectional"),
                            "external_updated_at": external_updated_at.isoformat() if isinstance(external_updated_at, datetime) else external_updated_at,
                            "last_synced_at": datetime.utcnow().isoformat(),
                        }
                        
                        supabase.table("raw_tasks").insert(task_data).execute()
                        created_count += 1
                    
                    synced_count += 1
                except Exception as e:
                    error_msg = f"Failed to sync task {external_task.get('id', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    StructuredLogger.log_event(
                        "sync_task_error",
                        error_msg,
                        user_id=user_id,
                        metadata={"external_task_id": external_task.get("id")},
                        level="WARNING"
                    )
            
            StructuredLogger.log_event(
                "sync_inbound_complete",
                f"Inbound sync completed: {synced_count} synced, {created_count} created, {updated_count} updated, {len(conflicts)} conflicts",
                user_id=user_id,
                metadata={
                    "synced_count": synced_count,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "conflicts_count": len(conflicts),
                    "errors_count": len(errors),
                },
            )
            
            return {
                "success": True,
                "synced_count": synced_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "conflicts": conflicts,
                "errors": errors,
            }
        except TaskManagerIntegrationError as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "sync_tasks_inbound"})
            raise
        except Exception as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "sync_tasks_inbound"})
            raise TaskManagerIntegrationError(f"Inbound sync failed: {str(e)}")
    
    @error_handler
    async def sync_tasks_outbound(
        self,
        user_id: str,
        provider: str = "todoist"
    ) -> Dict:
        """Push LifeFlow task changes to external task manager"""
        if provider not in self.integrations:
            raise TaskManagerIntegrationError(f"Unsupported provider: {provider}")
        
        integration = self.integrations[provider]
        
        try:
            StructuredLogger.log_event(
                "sync_outbound_start",
                f"Starting outbound sync to {provider}",
                user_id=user_id,
            )
            
            # Fetch tasks that need to be synced outbound
            # Get tasks that were modified locally and have sync_direction including outbound
            tasks_response = supabase.table("raw_tasks").select("*").eq(
                "user_id", user_id
            ).eq("source", provider).in_(
                "sync_direction", ["outbound", "bidirectional"]
            ).execute()
            
            synced_count = 0
            created_count = 0
            updated_count = 0
            errors = []
            
            for task_data in tasks_response.data:
                try:
                    external_id = task_data.get("external_id")
                    sync_status = task_data.get("sync_status", "pending")
                    
                    # Skip tasks with conflicts or errors
                    if sync_status in ["conflict", "error"]:
                        continue
                    
                    # Map to external format
                    mapped_task = integration.map_from_raw_task(task_data)
                    
                    if external_id:
                        # Update existing task
                        await integration.update_task(user_id, external_id, mapped_task)
                        updated_count += 1
                    else:
                        # Create new task
                        created_task = await integration.create_task(user_id, mapped_task)
                        external_id = str(created_task.get("id"))
                        
                        # Update local task with external_id
                        supabase.table("raw_tasks").update({
                            "external_id": external_id,
                            "sync_status": "synced",
                            "last_synced_at": datetime.utcnow().isoformat(),
                            "sync_error": None,
                        }).eq("id", task_data["id"]).execute()
                        
                        created_count += 1
                    
                    synced_count += 1
                except Exception as e:
                    error_msg = f"Failed to sync task {task_data.get('id', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    
                    # Mark task as error
                    supabase.table("raw_tasks").update({
                        "sync_status": "error",
                        "sync_error": str(e),
                    }).eq("id", task_data["id"]).execute()
                    
                    StructuredLogger.log_event(
                        "sync_task_error",
                        error_msg,
                        user_id=user_id,
                        metadata={"task_id": task_data.get("id")},
                        level="WARNING"
                    )
            
            StructuredLogger.log_event(
                "sync_outbound_complete",
                f"Outbound sync completed: {synced_count} synced, {created_count} created, {updated_count} updated",
                user_id=user_id,
                metadata={
                    "synced_count": synced_count,
                    "created_count": created_count,
                    "updated_count": updated_count,
                    "errors_count": len(errors),
                },
            )
            
            return {
                "success": True,
                "synced_count": synced_count,
                "created_count": created_count,
                "updated_count": updated_count,
                "errors": errors,
            }
        except TaskManagerIntegrationError as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "sync_tasks_outbound"})
            raise
        except Exception as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "sync_tasks_outbound"})
            raise TaskManagerIntegrationError(f"Outbound sync failed: {str(e)}")
    
    @error_handler
    async def sync_tasks_bidirectional(
        self,
        user_id: str,
        provider: str = "todoist"
    ) -> Dict:
        """Perform full bidirectional sync"""
        try:
            # First, pull from external (inbound)
            inbound_result = await self.sync_tasks_inbound(user_id, provider)
            
            # Then, push local changes (outbound)
            outbound_result = await self.sync_tasks_outbound(user_id, provider)
            
            return {
                "success": True,
                "inbound": inbound_result,
                "outbound": outbound_result,
            }
        except Exception as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "sync_tasks_bidirectional"})
            raise TaskManagerIntegrationError(f"Bidirectional sync failed: {str(e)}")
    
    @error_handler
    async def resolve_conflict(
        self,
        user_id: str,
        task_id: str,
        resolution: str,
        provider: str = "todoist"
    ) -> Dict:
        """Resolve a sync conflict"""
        if provider not in self.integrations:
            raise TaskManagerIntegrationError(f"Unsupported provider: {provider}")
        
        integration = self.integrations[provider]
        
        try:
            # Get task
            task_response = supabase.table("raw_tasks").select("*").eq(
                "user_id", user_id
            ).eq("id", task_id).execute()
            
            if not task_response.data:
                raise TaskManagerIntegrationError("Task not found")
            
            task_data = task_response.data[0]
            
            if resolution == "local":
                # Use local version - push to external
                mapped_task = integration.map_from_raw_task(task_data)
                external_id = task_data.get("external_id")
                
                if external_id:
                    await integration.update_task(user_id, external_id, mapped_task)
                
                # Update sync status
                supabase.table("raw_tasks").update({
                    "sync_status": "synced",
                    "sync_error": None,
                    "last_synced_at": datetime.utcnow().isoformat(),
                }).eq("id", task_id).execute()
            elif resolution == "external":
                # Use external version - pull from external
                external_id = task_data.get("external_id")
                if external_id:
                    # Fetch from external
                    external_tasks = await integration.fetch_tasks(user_id)
                    external_task = next(
                        (t for t in external_tasks if str(t.get("id")) == external_id),
                        None
                    )
                    
                    if external_task:
                        mapped_task = integration.map_to_raw_task(external_task, user_id)
                        
                        # Update local task
                        update_data = {
                            "title": mapped_task.get("title"),
                            "description": mapped_task.get("description"),
                            "start_time": mapped_task.get("start_time").isoformat() if isinstance(mapped_task.get("start_time"), datetime) else mapped_task.get("start_time"),
                            "end_time": mapped_task.get("end_time").isoformat() if isinstance(mapped_task.get("end_time"), datetime) else mapped_task.get("end_time"),
                            "extracted_priority": mapped_task.get("extracted_priority"),
                            "is_critical": mapped_task.get("is_critical", False),
                            "is_urgent": mapped_task.get("is_urgent", False),
                            "raw_data": mapped_task.get("raw_data", {}),
                            "sync_status": "synced",
                            "sync_error": None,
                            "last_synced_at": datetime.utcnow().isoformat(),
                        }
                        
                        supabase.table("raw_tasks").update(update_data).eq("id", task_id).execute()
            
            StructuredLogger.log_event(
                "conflict_resolved",
                f"Resolved conflict for task {task_id} using {resolution} version",
                user_id=user_id,
                metadata={"task_id": task_id, "resolution": resolution},
            )
            
            return {"success": True, "resolution": resolution}
        except Exception as e:
            StructuredLogger.log_error(e, context={"user_id": user_id, "function": "resolve_conflict"})
            raise TaskManagerIntegrationError(f"Failed to resolve conflict: {str(e)}")
    
    @error_handler
    async def update_sync_status(
        self,
        user_id: str,
        task_id: str,
        status: str,
        error: Optional[str] = None
    ):
        """Update sync status for a task"""
        update_data = {
            "sync_status": status,
            "last_synced_at": datetime.utcnow().isoformat(),
        }
        
        if error:
            update_data["sync_error"] = error
        
        supabase.table("raw_tasks").update(update_data).eq(
            "user_id", user_id
        ).eq("id", task_id).execute()


# Global sync service instance
task_sync_service = TaskSyncService()

