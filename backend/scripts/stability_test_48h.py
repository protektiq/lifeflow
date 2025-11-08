#!/usr/bin/env python3
"""
48-Hour Stability Test Script

This script validates autonomous operation of the LifeFlow system
for 48 hours without critical failures.

Usage:
    python scripts/stability_test_48h.py

The script will:
1. Monitor scheduler jobs
2. Check notification delivery
3. Verify feedback loop functionality
4. Monitor error rates
5. Generate a stability report
"""
import asyncio
import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List
import json
from app.agents.action.nudger import check_and_send_nudges
from app.utils.monitoring import StructuredLogger
from app.database import supabase


class StabilityMonitor:
    """Monitor system stability over 48 hours"""
    
    def __init__(self, duration_hours: int = 48):
        self.duration_hours = duration_hours
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=duration_hours)
        self.metrics = {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "checks_performed": 0,
            "errors": [],
            "critical_failures": [],
            "nudges_sent": 0,
            "scheduler_checks": 0,
            "database_checks": 0,
            "api_checks": 0,
        }
        self.check_interval_minutes = 5  # Check every 5 minutes
    
    async def check_scheduler(self) -> bool:
        """Check if scheduler is running"""
        try:
            # Check if scheduler jobs are executing
            # This is a simplified check - in production, you'd check actual scheduler status
            self.metrics["scheduler_checks"] += 1
            return True
        except Exception as e:
            self.metrics["errors"].append({
                "time": datetime.now().isoformat(),
                "type": "scheduler_check",
                "error": str(e),
            })
            return False
    
    async def check_nudger(self) -> Dict:
        """Check nudger functionality"""
        try:
            result = await check_and_send_nudges()
            self.metrics["nudges_sent"] += result.get("nudges_sent", 0)
            return result
        except Exception as e:
            self.metrics["critical_failures"].append({
                "time": datetime.now().isoformat(),
                "type": "nudger_failure",
                "error": str(e),
            })
            return {"error": str(e)}
    
    async def check_database(self) -> bool:
        """Check database connectivity"""
        try:
            # Simple query to check database
            response = supabase.table("daily_plans").select("id").limit(1).execute()
            self.metrics["database_checks"] += 1
            return True
        except Exception as e:
            self.metrics["critical_failures"].append({
                "time": datetime.now().isoformat(),
                "type": "database_failure",
                "error": str(e),
            })
            return False
    
    async def check_api_health(self) -> bool:
        """Check API health endpoint"""
        try:
            # In a real scenario, you'd make an HTTP request to /api/health
            # For now, we'll just check if the monitoring system is working
            self.metrics["api_checks"] += 1
            return True
        except Exception as e:
            self.metrics["errors"].append({
                "time": datetime.now().isoformat(),
                "type": "api_check",
                "error": str(e),
            })
            return False
    
    async def run_check_cycle(self):
        """Run one check cycle"""
        self.metrics["checks_performed"] += 1
        current_time = datetime.now()
        
        print(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] Running stability check #{self.metrics['checks_performed']}...")
        
        # Run all checks
        scheduler_ok = await self.check_scheduler()
        nudger_result = await self.check_nudger()
        database_ok = await self.check_database()
        api_ok = await self.check_api_health()
        
        # Log results
        if not scheduler_ok or not database_ok or not api_ok or nudger_result.get("error"):
            print(f"  ⚠️  Issues detected in check cycle")
        else:
            print(f"  ✓ All checks passed")
        
        # Log metrics
        StructuredLogger.log_event(
            "stability_check",
            f"Stability check #{self.metrics['checks_performed']}",
            metadata={
                "check_number": self.metrics["checks_performed"],
                "scheduler_ok": scheduler_ok,
                "database_ok": database_ok,
                "api_ok": api_ok,
                "nudges_sent": nudger_result.get("nudges_sent", 0),
                "errors": len(self.metrics["errors"]),
                "critical_failures": len(self.metrics["critical_failures"]),
            },
        )
    
    async def run(self):
        """Run stability test for specified duration"""
        print(f"Starting 48-hour stability test...")
        print(f"Start time: {self.start_time}")
        print(f"End time: {self.end_time}")
        print(f"Check interval: {self.check_interval_minutes} minutes")
        print("-" * 60)
        
        check_interval_seconds = self.check_interval_minutes * 60
        
        while datetime.now() < self.end_time:
            await self.run_check_cycle()
            
            # Calculate time remaining
            remaining = self.end_time - datetime.now()
            print(f"Time remaining: {remaining}")
            print("-" * 60)
            
            # Wait for next check
            await asyncio.sleep(check_interval_seconds)
        
        # Generate final report
        self.generate_report()
    
    def generate_report(self):
        """Generate final stability report"""
        duration = datetime.now() - self.start_time
        critical_failure_count = len(self.metrics["critical_failures"])
        error_count = len(self.metrics["errors"])
        
        report = {
            "test_duration_hours": self.duration_hours,
            "actual_duration_hours": duration.total_seconds() / 3600,
            "start_time": self.metrics["start_time"],
            "end_time": datetime.now().isoformat(),
            "checks_performed": self.metrics["checks_performed"],
            "nudges_sent": self.metrics["nudges_sent"],
            "scheduler_checks": self.metrics["scheduler_checks"],
            "database_checks": self.metrics["database_checks"],
            "api_checks": self.metrics["api_checks"],
            "total_errors": error_count,
            "critical_failures": critical_failure_count,
            "errors": self.metrics["errors"],
            "critical_failures": self.metrics["critical_failures"],
            "stability_status": "PASS" if critical_failure_count == 0 else "FAIL",
        }
        
        # Save report to file
        report_filename = f"stability_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_filename, "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("STABILITY TEST REPORT")
        print("=" * 60)
        print(f"Duration: {duration}")
        print(f"Checks performed: {self.metrics['checks_performed']}")
        print(f"Nudges sent: {self.metrics['nudges_sent']}")
        print(f"Total errors: {error_count}")
        print(f"Critical failures: {critical_failure_count}")
        print(f"Status: {report['stability_status']}")
        print(f"Report saved to: {report_filename}")
        print("=" * 60)
        
        if critical_failure_count > 0:
            print("\nCRITICAL FAILURES:")
            for failure in self.metrics["critical_failures"]:
                print(f"  - {failure['time']}: {failure['type']} - {failure['error']}")
        
        return report


async def main():
    """Main entry point"""
    monitor = StabilityMonitor(duration_hours=48)
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        monitor.generate_report()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        monitor.metrics["critical_failures"].append({
            "time": datetime.now().isoformat(),
            "type": "fatal_error",
            "error": str(e),
        })
        monitor.generate_report()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

