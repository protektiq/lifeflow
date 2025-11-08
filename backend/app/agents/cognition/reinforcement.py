"""Reinforcement Agent - Rule-based scoring for task fit"""
from typing import Dict, Optional
from datetime import datetime, timedelta
import math


def score_task_fit(
    raw_task: dict,
    energy_level: int,
    time_constraints: Optional[Dict] = None
) -> float:
    """
    Rule-based scoring algorithm to determine task fit
    
    Args:
        raw_task: Raw task dictionary
        energy_level: User's energy level (1-5)
        time_constraints: Optional global time constraints
    
    Returns:
        Normalized score (0-1) indicating task fit
    """
    # Base score from priority
    priority_score = _get_priority_score(raw_task.get("extracted_priority"))
    
    # Energy adjustment
    energy_score = _get_energy_fit_score(raw_task, energy_level)
    
    # Time constraint validation
    time_score = _get_time_constraint_score(raw_task, time_constraints)
    
    # Critical/urgent override multiplier
    override_multiplier = _get_override_multiplier(raw_task)
    
    # Combine scores
    base_score = (priority_score * 0.3) + (energy_score * 0.4) + (time_score * 0.3)
    
    # Apply override multiplier
    final_score = base_score * override_multiplier
    
    # Normalize to 0-1 range
    return max(0.0, min(1.0, final_score))


def _get_priority_score(priority: Optional[str]) -> float:
    """Convert priority string to numeric score"""
    priority_map = {
        "high": 1.0,
        "medium": 0.7,
        "low": 0.4,
        "normal": 0.5,
    }
    return priority_map.get(priority or "normal", 0.5)


def _get_energy_fit_score(raw_task: dict, energy_level: int) -> float:
    """
    Calculate energy fit score
    High energy tasks (complex, long duration) match high energy levels
    Low energy tasks (simple, short) match low energy levels
    """
    # Estimate task complexity from duration and description
    start_time = datetime.fromisoformat(raw_task["start_time"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(raw_task["end_time"].replace("Z", "+00:00"))
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    # Estimate complexity
    description_length = len(raw_task.get("description", "") or "")
    has_attendees = len(raw_task.get("attendees", [])) > 0
    
    # Complex tasks: long duration, detailed description, or meetings
    complexity_score = 0.5  # Default medium
    if duration_minutes > 60:
        complexity_score = 0.8  # Long task
    elif duration_minutes > 30:
        complexity_score = 0.6
    elif duration_minutes < 15:
        complexity_score = 0.3  # Short task
    
    if description_length > 200:
        complexity_score = min(1.0, complexity_score + 0.2)
    
    if has_attendees:
        complexity_score = min(1.0, complexity_score + 0.1)  # Meetings are more complex
    
    # Calculate fit: how well energy level matches task complexity
    # Normalize energy level to 0-1 (1->0.2, 5->1.0)
    normalized_energy = (energy_level - 1) / 4.0
    
    # Fit score: inverse distance between complexity and energy
    fit_score = 1.0 - abs(complexity_score - normalized_energy)
    
    return max(0.0, fit_score)


def _get_time_constraint_score(
    raw_task: dict,
    time_constraints: Optional[Dict] = None
) -> float:
    """
    Validate time constraints
    Returns 1.0 if constraints are met, lower score if violated
    """
    if not time_constraints:
        return 1.0
    
    start_time = datetime.fromisoformat(raw_task["start_time"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(raw_task["end_time"].replace("Z", "+00:00"))
    
    # Check if task fits within global time window
    global_start = time_constraints.get("start")
    global_end = time_constraints.get("end")
    
    if global_start and global_end:
        global_start_dt = datetime.fromisoformat(global_start.replace("Z", "+00:00"))
        global_end_dt = datetime.fromisoformat(global_end.replace("Z", "+00:00"))
        
        # Task must fit within global window
        if start_time < global_start_dt or end_time > global_end_dt:
            return 0.3  # Partial fit penalty
    
    return 1.0


def _get_override_multiplier(raw_task: dict) -> float:
    """
    Critical/urgent override multiplier
    Critical tasks get high multiplier regardless of other factors
    """
    is_critical = raw_task.get("is_critical", False)
    is_urgent = raw_task.get("is_urgent", False)
    
    if is_critical:
        return 2.0  # Double the score
    elif is_urgent:
        return 1.5  # 50% boost
    
    return 1.0  # No override

