"""Monitoring, logging, and error tracking utilities"""
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
from fastapi import Request
import time

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger("lifeflow")


class StructuredLogger:
    """Structured JSON logging"""
    
    @staticmethod
    def log_event(
        event_type: str,
        message: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        level: str = "INFO"
    ):
        """Log structured event"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "message": message,
            "level": level,
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if metadata:
            log_data["metadata"] = metadata
        
        log_message = json.dumps(log_data)
        
        if level == "ERROR":
            logger.error(log_message)
        elif level == "WARNING":
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ):
        """Log error with full context"""
        StructuredLogger.log_event(
            event_type="error",
            message=str(error),
            user_id=user_id,
            metadata={
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc(),
                "context": context or {},
            },
            level="ERROR"
        )


class IngestionMetrics:
    """Track ingestion metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "total_events": 0,
            "successful_ingestions": 0,
            "failed_ingestions": 0,
            "processing_times": [],
            "last_sync": None,
        }
    
    def record_ingestion(
        self,
        success: bool,
        processing_time: float,
        event_count: int = 1
    ):
        """Record ingestion attempt"""
        self.metrics["total_events"] += event_count
        
        if success:
            self.metrics["successful_ingestions"] += event_count
        else:
            self.metrics["failed_ingestions"] += event_count
        
        self.metrics["processing_times"].append(processing_time)
        self.metrics["last_sync"] = datetime.utcnow().isoformat()
        
        # Keep only last 100 processing times
        if len(self.metrics["processing_times"]) > 100:
            self.metrics["processing_times"] = self.metrics["processing_times"][-100:]
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        total = self.metrics["successful_ingestions"] + self.metrics["failed_ingestions"]
        if total == 0:
            return 0.0
        return (self.metrics["successful_ingestions"] / total) * 100
    
    def get_avg_processing_time(self) -> float:
        """Calculate average processing time"""
        if not self.metrics["processing_times"]:
            return 0.0
        return sum(self.metrics["processing_times"]) / len(self.metrics["processing_times"])
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        return {
            **self.metrics,
            "success_rate": self.get_success_rate(),
            "avg_processing_time": self.get_avg_processing_time(),
        }


# Global metrics instance
ingestion_metrics = IngestionMetrics()


def track_ingestion(func):
    """Decorator to track ingestion performance"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        success = False
        event_count = 0
        
        try:
            result = await func(*args, **kwargs)
            success = True
            if isinstance(result, dict) and "event_count" in result:
                event_count = result["event_count"]
            elif isinstance(result, list):
                event_count = len(result)
            return result
        except Exception as e:
            StructuredLogger.log_error(e, context={"function": func.__name__})
            raise
        finally:
            processing_time = time.time() - start_time
            ingestion_metrics.record_ingestion(success, processing_time, event_count)
    
    return wrapper


def error_handler(func):
    """Decorator for error handling - handles both sync and async functions"""
    import inspect
    
    if inspect.iscoroutinefunction(func):
        # Function is async, wrap with async wrapper
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                StructuredLogger.log_error(e, context={"function": func.__name__})
                raise
        return async_wrapper
    else:
        # Function is sync, wrap with sync wrapper
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                StructuredLogger.log_error(e, context={"function": func.__name__})
                raise
        return sync_wrapper

