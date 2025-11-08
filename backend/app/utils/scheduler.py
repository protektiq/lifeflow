"""Background task scheduler for automatic daily plan generation"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import date, datetime
from app.database import supabase
from app.agents.orchestration.workflow import run_planning_workflow
from app.agents.action.nudger import check_and_send_nudges
from app.utils.monitoring import StructuredLogger
import asyncio


scheduler = AsyncIOScheduler()


async def generate_daily_plans_for_all_users():
    """Generate daily plans for all active users"""
    try:
        # Get all users (simplified - in production, filter by active users)
        # For now, we'll generate plans for users who have tasks
        today = date.today()
        
        # Get distinct user_ids from raw_tasks
        tasks_response = supabase.table("raw_tasks").select("user_id").execute()
        user_ids = list(set([task["user_id"] for task in tasks_response.data]))
        
        StructuredLogger.log_event(
            "scheduler_start",
            f"Starting daily plan generation for {len(user_ids)} users",
            metadata={"date": today.isoformat(), "user_count": len(user_ids)},
        )
        
        for user_id in user_ids:
            try:
                result = await run_planning_workflow(user_id, today)
                if result.get("success"):
                    StructuredLogger.log_event(
                        "scheduler_success",
                        f"Generated plan for user {user_id}",
                        user_id=user_id,
                        metadata={"date": today.isoformat()},
                    )
                else:
                    StructuredLogger.log_event(
                        "scheduler_error",
                        f"Failed to generate plan for user {user_id}",
                        user_id=user_id,
                        metadata={"errors": result.get("errors", [])},
                        level="WARNING",
                    )
            except Exception as e:
                StructuredLogger.log_error(
                    e,
                    context={"user_id": user_id, "function": "generate_daily_plans_for_all_users"},
                )
    except Exception as e:
        StructuredLogger.log_error(e, context={"function": "generate_daily_plans_for_all_users"})


async def check_and_send_nudges_job():
    """Wrapper for nudger check function with error handling"""
    try:
        result = await check_and_send_nudges()
        if result.get("error"):
            StructuredLogger.log_event(
                "scheduler_nudger_error",
                f"Nudger job encountered error: {result.get('error')}",
                metadata=result,
                level="WARNING",
            )
    except Exception as e:
        StructuredLogger.log_error(
            e,
            context={"function": "check_and_send_nudges_job"},
        )


def start_scheduler():
    """Start the background scheduler"""
    if scheduler.running:
        return
    
    # Schedule daily plan generation at 6:00 AM
    scheduler.add_job(
        generate_daily_plans_for_all_users,
        trigger=CronTrigger(hour=6, minute=0),
        id="daily_plan_generation",
        name="Generate daily plans for all users",
        replace_existing=True,
    )
    
    # Schedule nudge checking every 2 minutes
    scheduler.add_job(
        check_and_send_nudges_job,
        trigger=IntervalTrigger(minutes=2),
        id="check_and_send_nudges",
        name="Check and send micro-nudges for due tasks",
        replace_existing=True,
    )
    
    scheduler.start()
    
    nudger_job = scheduler.get_job("check_and_send_nudges")
    plan_job = scheduler.get_job("daily_plan_generation")
    
    StructuredLogger.log_event(
        "scheduler_initialized",
        "Background scheduler started",
        metadata={
            "next_plan_generation": str(plan_job.next_run_time) if plan_job else None,
            "next_nudge_check": str(nudger_job.next_run_time) if nudger_job else None,
        },
    )


def shutdown_scheduler():
    """Shutdown the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        StructuredLogger.log_event(
            "scheduler_shutdown",
            "Background scheduler stopped",
        )

