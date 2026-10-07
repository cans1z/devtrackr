"""Analytics and metrics routes."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_active_user, get_db
from ..models import Task, TaskStatus, User
from ..schemas import CategoryBreakdown, TaskMetrics, WeeklyStats

router = APIRouter(prefix="/metrics", tags=["analytics"])


@router.get("/summary", response_model=TaskMetrics)
def get_task_summary(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get overall task summary statistics for the authenticated user."""

    # Get total counts by status
    status_counts = (
        db.query(Task.status, func.count(Task.id).label("count"))
        .filter(Task.owner_id == current_user.id, Task.is_archived.is_(False))
        .group_by(Task.status)
        .all()
    )

    # Convert to dict for easy lookup
    status_dict = {status: count for status, count in status_counts}

    # Calculate completion rate
    total_tasks = sum(status_dict.values())
    completed_tasks = status_dict.get(TaskStatus.done, 0)
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # Get time tracking totals
    time_stats = (
        db.query(
            func.sum(Task.estimated_minutes).label("total_estimated"),
            func.sum(Task.actual_minutes).label("total_actual"),
        )
        .filter(Task.owner_id == current_user.id, Task.is_archived.is_(False))
        .first()
    )

    return TaskMetrics(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        in_progress_tasks=status_dict.get(TaskStatus.in_progress, 0),
        todo_tasks=status_dict.get(TaskStatus.todo, 0),
        total_estimated_minutes=time_stats.total_estimated,
        total_actual_minutes=time_stats.total_actual,
        completion_rate=round(completion_rate, 2),
    )


@router.get("/categories", response_model=list[CategoryBreakdown])
def get_category_breakdown(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get task breakdown by category with time tracking."""

    # Get category statistics
    category_stats = (
        db.query(
            Task.category,
            func.count(Task.id).label("count"),
            func.sum(Task.estimated_minutes).label("estimated_minutes"),
            func.sum(Task.actual_minutes).label("actual_minutes"),
        )
        .filter(
            Task.owner_id == current_user.id,
            Task.is_archived.is_(False),
            Task.category.isnot(None),
        )
        .group_by(Task.category)
        .all()
    )

    return [
        CategoryBreakdown(
            category=stat.category,
            count=stat.count,
            estimated_minutes=stat.estimated_minutes,
            actual_minutes=stat.actual_minutes,
        )
        for stat in category_stats
    ]


@router.get("/weekly", response_model=list[WeeklyStats])
def get_weekly_stats(
    weeks: int = Query(4, ge=1, le=12, description="Number of weeks to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get weekly productivity statistics for the specified number of weeks."""

    weekly_stats = []
    today = datetime.now(UTC)

    for week_offset in range(weeks):
        # Calculate week boundaries
        week_end = today - timedelta(weeks=week_offset)
        week_start = week_end - timedelta(days=6)

        # Get tasks completed in this week
        week_tasks = (
            db.query(
                func.count(Task.id).label("tasks_completed"),
                func.sum(Task.actual_minutes).label("total_time_spent"),
            )
            .filter(
                Task.owner_id == current_user.id,
                Task.status == TaskStatus.done,
                Task.updated_at >= week_start,
                Task.updated_at <= week_end,
            )
            .first()
        )

        # Calculate productivity score (completion rate + time efficiency)
        # This is a simple scoring system - you can make it more sophisticated
        productivity_score = 0.0
        if week_tasks.tasks_completed and week_tasks.tasks_completed > 0:
            # Base score from completion count (0-50 points)
            completion_score = min(week_tasks.tasks_completed * 10, 50)

            # Time efficiency bonus (0-50 points)
            time_score = 0
            if week_tasks.total_time_spent and week_tasks.total_time_spent > 0:
                # Reward efficient time usage (more tasks in less time = higher score)
                time_score = min(
                    50,
                    (week_tasks.tasks_completed * 60)
                    / week_tasks.total_time_spent
                    * 25,
                )

            productivity_score = min(100, completion_score + time_score)

        weekly_stats.append(
            WeeklyStats(
                week_start=week_start,
                week_end=week_end,
                tasks_completed=week_tasks.tasks_completed or 0,
                total_time_spent=week_tasks.total_time_spent,
                productivity_score=round(productivity_score, 2),
            )
        )

    return weekly_stats


@router.get("/time-efficiency")
def get_time_efficiency(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)
):
    """Get time efficiency metrics comparing estimated vs actual time."""

    # Get tasks with both estimated and actual time
    time_comparison = (
        db.query(
            func.avg(Task.estimated_minutes).label("avg_estimated"),
            func.avg(Task.actual_minutes).label("avg_actual"),
            func.count(Task.id).label("total_tasks_tracked"),
        )
        .filter(
            Task.owner_id == current_user.id,
            Task.is_archived.is_(False),
            Task.estimated_minutes.isnot(None),
            Task.actual_minutes.isnot(None),
            Task.actual_minutes > 0,
        )
        .first()
    )

    if not time_comparison.total_tasks_tracked:
        return {
            "message": "No time tracking data available",
            "total_tasks_tracked": 0,
        }

    # Calculate efficiency metrics
    avg_estimated = time_comparison.avg_estimated or 0
    avg_actual = time_comparison.avg_actual or 0

    efficiency_ratio = avg_estimated / avg_actual if avg_actual > 0 else 0
    accuracy_percentage = (
        (1 - abs(avg_estimated - avg_actual) / avg_estimated) * 100
        if avg_estimated > 0
        else 0
    )

    return {
        "total_tasks_tracked": time_comparison.total_tasks_tracked,
        "average_estimated_minutes": round(avg_estimated, 2),
        "average_actual_minutes": round(avg_actual, 2),
        "efficiency_ratio": round(
            efficiency_ratio, 2
        ),  # >1 = overestimated, <1 = underestimated
        "accuracy_percentage": round(accuracy_percentage, 2),
        "interpretation": {
            "efficiency_ratio": "Ratio of estimated to actual time. >1 means you overestimate, <1 means you underestimate.",
            "accuracy_percentage": "How accurate your time estimates are (100% = perfect estimates)",
        },
    }


@router.get("/productivity-trends")
def get_productivity_trends(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get daily productivity trends over the specified period."""

    # Get daily completion counts
    daily_stats = (
        db.query(
            func.date(Task.updated_at).label("date"),
            func.count(Task.id).label("tasks_completed"),
        )
        .filter(
            Task.owner_id == current_user.id,
            Task.status == TaskStatus.done,
            Task.updated_at >= datetime.now(UTC) - timedelta(days=days),
            Task.is_archived.is_(False),
        )
        .group_by(func.date(Task.updated_at))
        .order_by(func.date(Task.updated_at))
        .all()
    )

    # Convert to list of daily data
    daily_data = [
        {"date": stat.date.isoformat(), "tasks_completed": stat.tasks_completed}
        for stat in daily_stats
    ]

    # Calculate trend metrics
    if len(daily_data) >= 2:
        first_week_avg = sum(d["tasks_completed"] for d in daily_data[:7]) / min(
            7, len(daily_data)
        )
        last_week_avg = sum(d["tasks_completed"] for d in daily_data[-7:]) / min(
            7, len(daily_data)
        )
        trend_direction = (
            "improving"
            if last_week_avg > first_week_avg
            else "declining"
            if last_week_avg < first_week_avg
            else "stable"
        )
        trend_percentage = (
            ((last_week_avg - first_week_avg) / first_week_avg * 100)
            if first_week_avg > 0
            else 0
        )
    else:
        trend_direction = "insufficient_data"
        trend_percentage = 0

    return {
        "period_days": days,
        "daily_data": daily_data,
        "trend_analysis": {
            "direction": trend_direction,
            "percentage_change": round(trend_percentage, 2),
            "first_week_average": (
                round(first_week_avg, 2) if len(daily_data) >= 2 else 0
            ),
            "last_week_average": (
                round(last_week_avg, 2) if len(daily_data) >= 2 else 0
            ),
        },
    }


@router.get("/ping")
def ping():
    """Lightweight liveness check for the metrics router."""
    return {"status": "ok"}
