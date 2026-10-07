"""
Schemas package.

Re-exports all Pydantic schemas for convenient importing.
"""

from .activity import (
    ActivityLogListResponse,
    ActivityLogOut,
)
from .metrics import (
    CategoryBreakdown,
    TaskMetrics,
    WeeklyStats,
)
from .task import (
    SearchFilters,
    TaskBase,
    TaskCreate,
    TaskListResponse,
    TaskOut,
    TaskSearchResponse,
    TaskUpdate,
)
from .time_entry import (
    ActiveTimer,
    TimeEntryBase,
    TimeEntryCreate,
    TimeEntryOut,
    TimeEntryUpdate,
    TimerStart,
    TimerStop,
    TimeSummary,
)
from .user import (
    Token,
    TokenData,
    UserBase,
    UserCreate,
    UserLogin,
    UserOut,
    UserUpdate,
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "UserLogin",
    "Token",
    "TokenData",
    # Task schemas
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskOut",
    "TaskListResponse",
    "TaskSearchResponse",
    "SearchFilters",
    # Time entry schemas
    "TimeEntryBase",
    "TimeEntryCreate",
    "TimeEntryUpdate",
    "TimeEntryOut",
    "TimerStart",
    "TimerStop",
    "ActiveTimer",
    "TimeSummary",
    # Metrics schemas
    "TaskMetrics",
    "CategoryBreakdown",
    "WeeklyStats",
    # Activity schemas
    "ActivityLogOut",
    "ActivityLogListResponse",
]
