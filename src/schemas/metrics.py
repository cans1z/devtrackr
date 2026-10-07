"""Metrics-related schemas."""

from datetime import datetime

from pydantic import BaseModel


class TaskMetrics(BaseModel):
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    todo_tasks: int
    total_estimated_minutes: int | None
    total_actual_minutes: int | None
    completion_rate: float  # Percentage of completed tasks


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    estimated_minutes: int | None
    actual_minutes: int | None


class WeeklyStats(BaseModel):
    week_start: datetime
    week_end: datetime
    tasks_completed: int
    total_time_spent: int | None  # in minutes
    productivity_score: float  # based on completion rate and time efficiency
