"""
Base model configuration and enums.

Provides the SQLAlchemy Base class and shared enumerations.
"""

from enum import StrEnum

from ..core.database import Base

# --- Комментарии реверс-инжиниринга (анализ студента) ---------------------
# Все перечисления ниже наследуются от StrEnum: это значит, что значения
# enum'ов хранятся в БД и сериализуются в JSON как обычные строки
# ("todo", "in_progress" и т.д.), а не как числа. Это удобно для отладки
# и совместимо с Pydantic-схемами без дополнительных конвертеров.


class TaskStatus(StrEnum):
    # Линейный жизненный цикл задачи. Прямых ограничений на переходы
    # (нельзя из todo сразу в done, например) в коде НЕ обнаружено —
    # эндпоинт PATCH /tasks/{id} принимает любое значение из enum.
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class TimeEntryStatus(StrEnum):
    # ВАЖНО: значение "paused" объявлено, но в src/routes/time_tracking.py
    # нет ни одного эндпоинта, который бы его устанавливал (нет ручки
    # "поставить таймер на паузу"). Судя по всему, это задел на будущее
    # расширение API, который пока не реализован.
    active = "active"
    paused = "paused"
    completed = "completed"


class ActivityType(StrEnum):
    """Activity types for the activity log."""

    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_ARCHIVED = "task_archived"
    TASK_UNARCHIVED = "task_unarchived"
    TIMER_STARTED = "timer_started"
    TIMER_STOPPED = "timer_stopped"


__all__ = [
    "Base",
    "TaskStatus",
    "TaskPriority",
    "TimeEntryStatus",
    "ActivityType",
]
