"""
Activity logging service for tracking user actions.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ..models import ActivityLog, ActivityType


class ActivityLogger:
    """Service for logging user activities.

    [Анализ] Класс реализует паттерн Facade поверх ActivityLog: набор
    именованных статических методов (log_task_created, log_timer_started
    и т.д.) — это просто удобные обёртки вокруг универсального
    log_activity(), которые фиксируют "словарь" activity_type/entity_type/
    description для каждого типа события, чтобы вызывающий код в routes/*
    не формировал эти поля вручную и не мог случайно опечататься в строке
    activity_type.
    """

    @staticmethod
    def log_activity(
        db: Session,
        user_id: int,
        activity_type: ActivityType,
        entity_type: str,
        entity_id: int | None,
        description: str,
        activity_metadata: dict[str, Any] | None = None,
    ) -> ActivityLog:
        """
        Log an activity for a user.

        Args:
            db: Database session
            user_id: ID of the user performing the action
            activity_type: Type of activity being logged
            entity_type: Type of entity affected (e.g., "task", "time_entry")
            entity_id: ID of the affected entity
            description: Human-readable description of the activity
            activity_metadata: Additional data about the activity

        Returns:
            The created ActivityLog instance

        [Анализ] ВАЖНАЯ ДЕТАЛЬ ДЛЯ АНАЛИЗА: этот метод сам вызывает
        db.commit(). Во всех местах вызова (routes/tasks.py,
        routes/time_tracking.py) основная сущность (задача, таймер)
        коммитится ОТДЕЛЬНЫМ, более ранним db.commit(), а уже ПОСЛЕ
        этого вызывается ActivityLogger.log_*(...). Таким образом,
        запись бизнес-сущности и запись в журнал активности — это ДВЕ
        независимые транзакции, а не одна атомарная операция: если
        логирование упадёт с исключением, задача (или запись времени)
        всё равно останется сохранённой в БД, просто без
        соответствующей записи в журнале активности.
        """
        activity = ActivityLog(
            user_id=user_id,
            activity_type=activity_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            activity_metadata=activity_metadata or {},
            created_at=datetime.now(UTC),
        )

        db.add(activity)
        db.commit()
        db.refresh(activity)

        return activity

    @staticmethod
    def log_task_created(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
    ) -> ActivityLog:
        """Log task creation."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_CREATED,
            entity_type="task",
            entity_id=task_id,
            description=f"Created task: {task_title}",
            activity_metadata={"task_title": task_title},
        )

    @staticmethod
    def log_task_updated(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
        changes: dict[str, Any],
    ) -> ActivityLog:
        """Log task updates."""
        changed_fields = list(changes.keys())
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_UPDATED,
            entity_type="task",
            entity_id=task_id,
            description=f"Updated task: {task_title}",
            activity_metadata={
                "task_title": task_title,
                "changed_fields": changed_fields,
                "changes": changes,
            },
        )

    @staticmethod
    def log_task_deleted(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
    ) -> ActivityLog:
        """Log task deletion (archiving)."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_DELETED,
            entity_type="task",
            entity_id=task_id,
            description=f"Deleted task: {task_title}",
            activity_metadata={"task_title": task_title},
        )

    @staticmethod
    def log_task_archived(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
    ) -> ActivityLog:
        """Log task archiving."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_ARCHIVED,
            entity_type="task",
            entity_id=task_id,
            description=f"Archived task: {task_title}",
            activity_metadata={"task_title": task_title},
        )

    @staticmethod
    def log_timer_started(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
    ) -> ActivityLog:
        """Log timer start."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TIMER_STARTED,
            entity_type="task",
            entity_id=task_id,
            description=f"Started timer for: {task_title}",
            activity_metadata={"task_title": task_title},
        )

    @staticmethod
    def log_timer_stopped(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
        duration_minutes: int,
    ) -> ActivityLog:
        """Log timer stop."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TIMER_STOPPED,
            entity_type="task",
            entity_id=task_id,
            description=f"Stopped timer for: {task_title} ({duration_minutes} minutes)",
            activity_metadata={
                "task_title": task_title,
                "duration_minutes": duration_minutes,
            },
        )

    @staticmethod
    def log_task_unarchived(
        db: Session,
        user_id: int,
        task_id: int,
        task_title: str,
    ) -> ActivityLog:
        """Log task unarchiving."""
        return ActivityLogger.log_activity(
            db=db,
            user_id=user_id,
            activity_type=ActivityType.TASK_UNARCHIVED,
            entity_type="task",
            entity_id=task_id,
            description=f"Unarchived task: {task_title}",
            activity_metadata={"task_title": task_title},
        )
