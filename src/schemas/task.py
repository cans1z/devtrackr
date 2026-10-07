"""Task-related schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.base import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    status: TaskStatus | None = None
    priority: TaskPriority | None = TaskPriority.medium
    due_date: datetime | None = None
    estimated_minutes: int | None = Field(None, ge=1)  # Minimum 1 minute
    actual_minutes: int | None = Field(None, ge=0)  # Minimum 0 minutes


class TaskCreate(TaskBase):
    title: str


class TaskUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = None
    description: str | None = None
    category: str | None = Field(None, max_length=100)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    estimated_minutes: int | None = Field(None, ge=1)
    actual_minutes: int | None = Field(None, ge=0)
    is_archived: bool | None = None


class TaskOut(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class TaskListResponse(BaseModel):
    """Paginated task list response"""

    items: list[TaskOut]
    next_cursor: str | None = None
    has_next: bool = False
    total_count: int | None = None


class TaskSearchResponse(BaseModel):
    """Search results response"""

    items: list[TaskOut]
    query: str
    total_matches: int
    search_time_ms: float
    suggestions: list[str] | None = None


class SearchFilters(BaseModel):
    """Search filters."""

    model_config = ConfigDict(str_strip_whitespace=True)

    status: TaskStatus | None = None
    category: str | None = None
    priority: TaskPriority | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    due_after: datetime | None = None
    due_before: datetime | None = None
    archived: bool | None = None
