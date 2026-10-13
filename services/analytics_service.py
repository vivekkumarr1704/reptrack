from __future__ import annotations
from datetime import date, timedelta
from typing import Iterable


def count_completed_workouts(workouts: Iterable[dict]) -> int:
    return sum(1 for w in workouts if w.get("status") == "completed")


def current_streak(workouts: Iterable[dict], today: date | None = None) -> int:
    """Consecutive calendar days ending today (or yesterday if no workout today)."""
    today = today or date.today()
    completed = {str(w.get("workout_date"))[:10] for w in workouts if w.get("status") == "completed"}
    day = today if today.isoformat() in completed else today - timedelta(days=1)
    streak = 0
    while day.isoformat() in completed:
        streak += 1
        day -= timedelta(days=1)
    return streak


def longest_streak(workouts: Iterable[dict]) -> int:
    dates = sorted({str(w.get("workout_date"))[:10] for w in workouts if w.get("status") == "completed"})
    if not dates: return 0
    longest = current = 1
    previous = date.fromisoformat(dates[0])
    for item in dates[1:]:
        day = date.fromisoformat(item)
        current = current + 1 if day == previous + timedelta(days=1) else 1
        longest = max(longest, current)
        previous = day
    return longest


def kg_to_unit(value: float, unit: str) -> float:
    return value * 2.2046226218 if unit == "lb" else value


def unit_to_kg(value: float, unit: str) -> float:
    return value / 2.2046226218 if unit == "lb" else value


def workout_volume(sets: Iterable[dict]) -> float:
    return sum(float(s.get("weight_kg") or 0) * int(s.get("reps") or 0) for s in sets if bool(s.get("completed", True)))


def total_reps(sets: Iterable[dict]) -> int:
    return sum(int(s.get("reps") or 0) for s in sets if bool(s.get("completed", True)))
