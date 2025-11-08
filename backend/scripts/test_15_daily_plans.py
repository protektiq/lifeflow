"""Test script to generate 15 consecutive daily plans for milestone validation"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import supabase
from app.agents.orchestration.workflow import run_planning_workflow
from app.utils.monitoring import StructuredLogger


async def test_15_consecutive_plans(user_id: str):
    """
    Generate 15 consecutive daily plans and validate they integrate
    time constraints and energy levels correctly
    """
    start_date = date.today()
    results = []
    
    print(f"Starting test: Generating 15 consecutive daily plans for user {user_id}")
    print(f"Start date: {start_date.isoformat()}\n")
    
    for day_offset in range(15):
        plan_date = start_date + timedelta(days=day_offset)
        print(f"Day {day_offset + 1}/15: Generating plan for {plan_date.isoformat()}")
        
        # Set a varying energy level (1-5) for testing
        energy_level = ((day_offset % 5) + 1)  # Cycle through 1-5
        
        # Store energy level
        try:
            supabase.table("daily_energy_levels").upsert({
                "user_id": user_id,
                "date": plan_date.isoformat(),
                "energy_level": energy_level,
            }).execute()
            print(f"  Set energy level: {energy_level}/5")
        except Exception as e:
            print(f"  Warning: Failed to set energy level: {e}")
        
        # Generate plan
        try:
            result = await run_planning_workflow(user_id, plan_date, energy_level)
            
            if result.get("success"):
                # Fetch the generated plan
                plan_response = supabase.table("daily_plans").select("*").eq(
                    "user_id", user_id
                ).eq("plan_date", plan_date.isoformat()).execute()
                
                if plan_response.data:
                    plan = plan_response.data[0]
                    task_count = len(plan.get("tasks", []))
                    plan_energy = plan.get("energy_level")
                    
                    print(f"  ✓ Plan generated successfully")
                    print(f"    Tasks: {task_count}")
                    print(f"    Energy level: {plan_energy}")
                    
                    # Validate time constraints
                    tasks = plan.get("tasks", [])
                    time_valid = True
                    for task in tasks:
                        predicted_start = task.get("predicted_start")
                        predicted_end = task.get("predicted_end")
                        if predicted_start and predicted_end:
                            if predicted_start >= predicted_end:
                                time_valid = False
                                print(f"    ⚠ Warning: Task {task.get('title')} has invalid time range")
                    
                    results.append({
                        "date": plan_date.isoformat(),
                        "success": True,
                        "task_count": task_count,
                        "energy_level": plan_energy,
                        "time_constraints_valid": time_valid,
                    })
                else:
                    print(f"  ✗ Plan generated but not found in database")
                    results.append({
                        "date": plan_date.isoformat(),
                        "success": False,
                        "error": "Plan not found in database",
                    })
            else:
                print(f"  ✗ Plan generation failed: {result.get('errors', ['Unknown error'])}")
                results.append({
                    "date": plan_date.isoformat(),
                    "success": False,
                    "errors": result.get("errors", []),
                })
        except Exception as e:
            print(f"  ✗ Exception: {e}")
            results.append({
                "date": plan_date.isoformat(),
                "success": False,
                "error": str(e),
            })
        
        print()
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    successful = sum(1 for r in results if r.get("success"))
    print(f"Successful plans: {successful}/15")
    print(f"Failed plans: {15 - successful}")
    
    if successful == 15:
        print("\n✓ MILESTONE ACHIEVED: All 15 consecutive daily plans generated successfully!")
    else:
        print(f"\n✗ MILESTONE NOT MET: Only {successful}/15 plans generated successfully")
    
    # Detailed results
    print("\nDetailed Results:")
    for result in results:
        status = "✓" if result.get("success") else "✗"
        print(f"{status} {result['date']}: ", end="")
        if result.get("success"):
            print(f"{result['task_count']} tasks, Energy: {result['energy_level']}/5, "
                  f"Time valid: {result.get('time_constraints_valid', 'N/A')}")
        else:
            print(f"Error: {result.get('error', result.get('errors', ['Unknown']))}")
    
    return results


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_15_daily_plans.py <user_id>")
        print("\nExample:")
        print("  python test_15_daily_plans.py 123e4567-e89b-12d3-a456-426614174000")
        sys.exit(1)
    
    user_id = sys.argv[1]
    results = await test_15_consecutive_plans(user_id)
    
    # Exit with error code if not all successful
    if not all(r.get("success") for r in results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

