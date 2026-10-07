"""Task management routes.

[Анализ] Самый крупный роутер в проекте: CRUD задач + полнотекстовый
поиск (see utils/search_utils.py, использует возможности PostgreSQL
full-text search) + курсорная пагинация (utils/pagination.py, вместо
постраничной OFFSET/LIMIT — так поиск остаётся быстрым на больших
объёмах данных, так как не требует пересчитывать смещение).
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import Session

from ..core.dependencies import get_current_active_user, get_db, get_user_task
from ..models import Task, TaskPriority, TaskStatus, User
from ..schemas import (
    SearchFilters,
    TaskCreate,
    TaskListResponse,
    TaskOut,
    TaskSearchResponse,
    TaskUpdate,
)
from ..services.activity_logger import ActivityLogger
from ..utils.pagination import create_task_cursor, get_pagination_params
from ..utils.search_utils import (
    build_search_query,
    calculate_search_stats,
    get_search_suggestions,
    normalize_search_query,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def apply_task_filters(
    stmt,
    status_: TaskStatus | None = None,
    category: str | None = None,
    due_before: datetime | None = None,
    archived: bool | None = None,
):
    """Apply common task filters to a SQLAlchemy query statement.

    [Анализ] Переиспользуемый билдер фильтров: и list_tasks(), и другие
    выборки задач опираются на эту функцию, чтобы логика фильтрации
    (по статусу/категории/сроку/архивации) не дублировалась в каждом
    отдельном эндпоинте.
    """
    if status_ is not None:
        stmt = stmt.where(Task.status == status_)
    if category is not None:
        stmt = stmt.where(Task.category == category)
    if due_before is not None:
        stmt = stmt.where(Task.due_date.isnot(None), Task.due_date <= due_before)
    if archived is not None:
        stmt = stmt.where(Task.is_archived == archived)
    return stmt


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new task for the authenticated user."""
    task = Task(
        title=payload.title,
        description=payload.description,
        category=payload.category,
        status=TaskStatus(payload.status) if payload.status else TaskStatus.todo,
        priority=payload.priority or TaskPriority.medium,
        due_date=payload.due_date,
        estimated_minutes=payload.estimated_minutes,
        actual_minutes=payload.actual_minutes,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Log activity
    ActivityLogger.log_task_created(
        db=db,
        user_id=current_user.id,
        task_id=task.id,
        task_title=task.title,
    )

    return task


@router.get("", response_model=TaskListResponse)
def list_tasks(
    cursor: str | None = Query(None, description="Cursor for pagination"),
    limit: int = Query(20, ge=1, le=100, description="Number of tasks per page"),
    status_: TaskStatus | None = Query(None, alias="status"),
    category: str | None = Query(None, description="Filter by category"),
    due_before: datetime | None = None,
    archived: bool | None = None,
    include_total: bool = Query(
        False, description="Include total count (expensive for large datasets)"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List tasks for the current user with cursor-based pagination and optional filters."""

    # Parse pagination parameters
    cursor_id, cursor_created_at, limit = get_pagination_params(cursor, limit)

    # Build base query
    stmt = select(Task).where(Task.owner_id == current_user.id)

    # Apply filters
    stmt = apply_task_filters(stmt, status_, category, due_before, archived)

    # Apply cursor-based pagination
    if cursor_id and cursor_created_at:
        # For cursor pagination, we need to handle the case where multiple tasks
        # have the same created_at timestamp by using ID as a tiebreaker
        stmt = stmt.where(
            or_(
                Task.created_at < cursor_created_at,
                and_(Task.created_at == cursor_created_at, Task.id < cursor_id),
            )
        )

    # Order by created_at desc, then by id desc for consistent pagination
    stmt = stmt.order_by(Task.created_at.desc(), Task.id.desc())

    # Get one extra item to determine if there's a next page
    stmt = stmt.limit(limit + 1)

    # Execute query
    tasks = db.execute(stmt).scalars().all()

    # Check if there are more items
    has_next = len(tasks) > limit
    if has_next:
        tasks = tasks[:limit]  # Remove the extra item

    # Create next cursor if there are more items
    next_cursor = None
    if has_next and tasks:
        last_task = tasks[-1]
        next_cursor = create_task_cursor(last_task.id, last_task.created_at)

    # Get total count if requested (expensive for large datasets)
    total_count = None
    if include_total:
        count_stmt = select(func.count(Task.id)).where(Task.owner_id == current_user.id)
        count_stmt = apply_task_filters(
            count_stmt, status_, category, due_before, archived
        )
        total_count = db.execute(count_stmt).scalar()

    return TaskListResponse(
        items=tasks, next_cursor=next_cursor, has_next=has_next, total_count=total_count
    )


@router.get("/search", response_model=TaskSearchResponse)
def search_tasks(
    q: str = Query(..., min_length=1, max_length=200, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    status_: TaskStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    category: str | None = Query(None, description="Filter by category"),
    priority: TaskPriority | None = Query(None, description="Filter by priority"),
    created_after: datetime | None = Query(
        None, description="Filter tasks created after this date"
    ),
    created_before: datetime | None = Query(
        None, description="Filter tasks created before this date"
    ),
    due_after: datetime | None = Query(
        None, description="Filter tasks due after this date"
    ),
    due_before: datetime | None = Query(
        None, description="Filter tasks due before this date"
    ),
    archived: bool | None = Query(None, description="Filter by archived status"),
    include_suggestions: bool = Query(True, description="Include search suggestions"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Search tasks using full-text search across titles and descriptions."""

    start_time = time.time()

    # Normalize search query
    normalized_query = normalize_search_query(q)
    if not normalized_query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty or contain only special characters",
        )

    # Build search filters
    filters = SearchFilters(
        status=status_,
        category=category,
        priority=priority,
        created_after=created_after,
        created_before=created_before,
        due_after=due_after,
        due_before=due_before,
        archived=archived,
    )

    # Build the search query
    search_sql, params = build_search_query(normalized_query, filters, current_user.id)

    # Add limit to the query
    search_sql += (
        f" LIMIT {limit + 1}"  # Get one extra to check if there are more results
    )

    # Execute search query
    try:
        result = db.execute(text(search_sql), params)
        tasks = result.fetchall()

        # Check if there are more results
        has_more = len(tasks) > limit
        if has_more:
            tasks = tasks[:limit]  # Remove the extra item

        # Convert to Task objects
        task_objects = []
        for row in tasks:
            # Create Task object from row data
            task = Task(
                id=row.id,
                title=row.title,
                description=row.description,
                category=row.category,
                status=TaskStatus(row.status),
                priority=TaskPriority(row.priority),
                due_date=row.due_date,
                estimated_minutes=row.estimated_minutes,
                actual_minutes=row.actual_minutes,
                is_archived=row.is_archived,
                owner_id=row.owner_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            task_objects.append(task)

        # Get total count for the search (without limit)
        count_sql = (
            search_sql.replace(
                "SELECT t.*, ts_rank(to_tsvector('english', t.title || ' ' || COALESCE(t.description, '')), plainto_tsquery('english', :query)) as rank",
                "SELECT COUNT(*) as total",
            ).split("ORDER BY")[0]
            + "LIMIT 1"
        )

        count_result = db.execute(text(count_sql), params)
        total_matches = count_result.scalar() or 0

        # Get search suggestions if requested
        suggestions = None
        if include_suggestions:
            suggestions = get_search_suggestions(db, current_user.id, normalized_query)

        # Calculate search statistics
        search_stats = calculate_search_stats(
            start_time, total_matches, normalized_query
        )

        return TaskSearchResponse(
            items=task_objects,
            query=normalized_query,
            total_matches=total_matches,
            search_time_ms=search_stats["search_time_ms"],
            suggestions=suggestions,
        )

    except Exception:
        # Log the error and return a user-friendly message
        raise HTTPException(
            status_code=500,
            detail="Search failed. Please try a different query or contact support.",
        )


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task: Task = Depends(get_user_task),
):
    """Get a specific task by ID (must belong to current user)."""
    return task


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    payload: TaskUpdate,
    task: Task = Depends(get_user_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a task (must belong to current user)."""

    updates = payload.model_dump(exclude_unset=True)
    if "status" in updates and updates["status"] is not None:
        updates["status"] = TaskStatus(updates["status"])
    if "priority" in updates and updates["priority"] is not None:
        updates["priority"] = TaskPriority(updates["priority"])

    # Track changes for activity logging
    changes = {}
    for field, value in updates.items():
        old_value = getattr(task, field, None)
        setattr(task, field, value)
        if old_value != value:
            changes[field] = {"old": old_value, "new": value}

    db.add(task)
    db.commit()
    db.refresh(task)

    # Log activity if there were changes
    if changes:
        ActivityLogger.log_task_updated(
            db=db,
            user_id=current_user.id,
            task_id=task.id,
            task_title=task.title,
            changes=changes,
        )

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    hard: bool = False,
    task: Task = Depends(get_user_task),
    db: Session = Depends(get_db),
):
    """Delete a task (soft delete by default, must belong to current user)."""

    if hard:
        db.delete(task)
    else:
        task.is_archived = True
        db.add(task)
    db.commit()
    return None


@router.post("/{task_id}/unarchive", response_model=TaskOut)
def unarchive_task(
    task: Task = Depends(get_user_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Unarchive a task (must belong to current user)."""

    if not task.is_archived:
        raise HTTPException(status_code=400, detail="Task is not archived")

    task.is_archived = False
    db.add(task)
    db.commit()
    db.refresh(task)

    # Log activity
    ActivityLogger.log_task_unarchived(
        db=db,
        user_id=current_user.id,
        task_id=task.id,
        task_title=task.title,
    )

    return task


@router.post("/{task_id}/start-timer")
def start_task_timer(
    task: Task = Depends(get_user_task),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Start timing a task (redirects to new time tracking system)."""
    # Redirect to new time tracking system
    from ..schemas import TimerStart
    from .time_tracking import start_timer

    timer_data = TimerStart(task_id=task.id)
    return start_timer(timer_data, db, current_user)


@router.post("/{task_id}/stop-timer")
def stop_task_timer(
    minutes_spent: int,
    task: Task = Depends(get_user_task),
    db: Session = Depends(get_db),
):
    """Stop timing a task and record time spent (legacy endpoint)."""

    # Update actual time spent (legacy behavior)
    if task.actual_minutes is None:
        task.actual_minutes = minutes_spent
    else:
        task.actual_minutes += minutes_spent

    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "message": "Timer stopped (legacy endpoint - consider using /time/stop/{time_entry_id})",
        "task_id": task.id,
        "total_minutes": task.actual_minutes,
    }
