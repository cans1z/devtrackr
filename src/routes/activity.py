"""
Activity log router for tracking and retrieving user activities.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_active_user, get_db
from ..models import ActivityLog, ActivityType, User
from ..schemas import ActivityLogListResponse
from ..utils.pagination import create_task_cursor, get_pagination_params

router = APIRouter()


@router.get("/activity", response_model=ActivityLogListResponse)
def get_activity_log(
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Number of activities per page"),
    activity_type: ActivityType | None = Query(
        None, description="Filter by activity type"
    ),
    include_total: bool = Query(
        False, description="Include total count (expensive for large datasets)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get recent activity log for the current user."""

    # Parse pagination parameters
    cursor_id, cursor_created_at, limit = get_pagination_params(cursor, limit)

    # Build base query
    stmt = select(ActivityLog).where(ActivityLog.user_id == current_user.id)

    # Apply activity type filter
    if activity_type is not None:
        stmt = stmt.where(ActivityLog.activity_type == activity_type)

    # Apply cursor-based pagination
    if cursor_id and cursor_created_at:
        stmt = stmt.where(
            and_(ActivityLog.created_at < cursor_created_at, ActivityLog.id < cursor_id)
        )

    # Order by created_at desc, then by id desc for consistent pagination
    stmt = stmt.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())

    # Get one extra item to determine if there's a next page
    stmt = stmt.limit(limit + 1)

    # Execute query
    activities = db.execute(stmt).scalars().all()

    # Check if there are more items
    has_next = len(activities) > limit
    if has_next:
        activities = activities[:limit]  # Remove the extra item

    # Create next cursor if there are more items
    next_cursor = None
    if has_next and activities:
        last_activity = activities[-1]
        next_cursor = create_task_cursor(last_activity.id, last_activity.created_at)

    # Get total count if requested
    total_count = None
    if include_total:
        count_stmt = select(func.count(ActivityLog.id)).where(
            ActivityLog.user_id == current_user.id
        )

        if activity_type is not None:
            count_stmt = count_stmt.where(ActivityLog.activity_type == activity_type)

        total_count = db.execute(count_stmt).scalar()

    return ActivityLogListResponse(
        items=activities,
        next_cursor=next_cursor,
        has_next=has_next,
        total_count=total_count,
    )


@router.get("/activity/summary")
def get_activity_summary(
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get activity summary for the current user."""

    # Calculate date range
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=days)

    # Get activity counts by type
    summary_query = (
        select(ActivityLog.activity_type, func.count(ActivityLog.id).label("count"))
        .where(
            and_(
                ActivityLog.user_id == current_user.id,
                ActivityLog.created_at >= start_date,
                ActivityLog.created_at <= end_date,
            )
        )
        .group_by(ActivityLog.activity_type)
    )

    results = db.execute(summary_query).all()

    # Format results
    activity_counts = {result.activity_type: result.count for result in results}

    # Get total activities
    total_query = select(func.count(ActivityLog.id)).where(
        and_(
            ActivityLog.user_id == current_user.id,
            ActivityLog.created_at >= start_date,
            ActivityLog.created_at <= end_date,
        )
    )
    total_activities = db.execute(total_query).scalar() or 0

    return {
        "period_days": days,
        "total_activities": total_activities,
        "activity_counts": activity_counts,
        "most_active_type": (
            max(activity_counts.items(), key=lambda x: x[1])[0]
            if activity_counts
            else None
        ),
    }
