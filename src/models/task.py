"""Task model definition."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base
from .base import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from .user import User


class Task(Base):
    # [Анализ] Центральная сущность предметной области. Одна задача может
    # иметь несколько записей TimeEntry (учёт времени 1:N). Поле
    # actual_minutes НЕ вычисляется на лету агрегацией по TimeEntry —
    # оно инкрементально обновляется напрямую в routes/time_tracking.py
    # при остановке таймера (denormalization для скорости чтения ценой
    # риска рассинхронизации, если запись времени будет удалена вручную).
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),  # Postgres ENUM type named "task_status"
        nullable=False,
        default=TaskStatus.todo,  # client-side default
        server_default=TaskStatus.todo.value,  # DB-side default
        index=True,
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(
            TaskPriority, name="task_priority"
        ),  # Postgres ENUM type named "task_priority"
        nullable=False,
        default=TaskPriority.medium,  # client-side default
        server_default=TaskPriority.medium.value,  # DB-side default
        index=True,
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    estimated_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Estimated time to complete
    actual_minutes: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Actual time spent

    # [Анализ] Мягкое удаление (soft delete): DELETE /tasks/{id} по
    # умолчанию просто выставляет is_archived=True, а не удаляет строку.
    # Жёсткое удаление возможно только явным параметром ?hard=true.
    is_archived: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )

    # User relationship
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    owner: Mapped[User] = relationship("User", back_populates="tasks")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # set by DB at insert
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),  # set by DB at insert
        onupdate=func.now(),  # set by ORM on UPDATE
    )

    # [Анализ] Составные индексы подобраны под конкретные запросы роутов:
    # (status, due_date) — под фильтрацию просроченных задач по статусу;
    # (owner_id, status) и (owner_id, priority) — под основной сценарий
    # "список МОИХ задач, отфильтрованный по статусу/приоритету", который
    # выполняется практически при каждом обращении к GET /tasks.
    __table_args__ = (
        Index("ix_tasks_status_due", "status", "due_date"),
        Index("ix_tasks_owner_status", "owner_id", "status"),
        # Removed duplicate priority index since priority column has index=True
        Index("ix_tasks_owner_priority", "owner_id", "priority"),
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} title={self.title!r} "
            f"status={self.status} priority={self.priority}>"
        )
