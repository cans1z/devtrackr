"""User model definition."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .activity import ActivityLog
    from .task import Task
    from .time_entry import TimeEntry


class User(Base):
    # [Анализ] Корневая сущность системы. И Task, и TimeEntry, и ActivityLog
    # ссылаются на User через owner_id/user_id — модель "одиночного
    # арендатора на пользователя" (каждый пользователь видит только свои
    # данные; изоляция обеспечивается на уровне запросов в routes/*.py
    # через фильтр WHERE owner_id == current_user.id, а не на уровне БД).
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    # [Анализ] Пароль никогда не хранится в открытом виде: см.
    # core/security.py — используется passlib + bcrypt (get_password_hash).
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # [Анализ] is_active используется в dependencies.get_current_active_user
    # как дополнительная проверка после проверки JWT — позволяет
    # "заблокировать" пользователя, не удаляя его запись и не отзывая
    # уже выданные токены по отдельности (сам JWT остаётся валидным до
    # истечения TTL, но запрос будет отклонён на этапе проверки is_active).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship to tasks
    # [Анализ] cascade="all, delete-orphan": при удалении пользователя
    # каскадно удаляются все его задачи, записи времени и записи журнала
    # активности (физическое удаление в БД, не архивация).
    tasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="owner", cascade="all, delete-orphan"
    )

    # Relationship to time entries
    time_entries: Mapped[list[TimeEntry]] = relationship(
        "TimeEntry", back_populates="owner", cascade="all, delete-orphan"
    )

    # Relationship to activity logs
    activity_logs: Mapped[list[ActivityLog]] = relationship(
        "ActivityLog", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} email={self.email!r}>"
