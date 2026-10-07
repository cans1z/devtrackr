"""ActivityLog model definition."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from ..core.database import Base
from .base import ActivityType

if TYPE_CHECKING:
    from .user import User  # noqa: F401


class ActivityLog(Base):
    """Activity log for tracking recent user actions."""

    # [Анализ] Это единственная модель, которая использует "старый" стиль
    # SQLAlchemy (Column(...) вместо Mapped[...]/mapped_column), в отличие
    # от User/Task/TimeEntry. Функционально эквивалентно, но указывает на
    # то, что этот файл, вероятно, писался раньше остальных моделей
    # (либо другим соглашением) — типичный сигнал при реверс-инжиниринге
    # эволюции кодовой базы.
    #
    # entity_type/entity_id — это неявный полиморфный внешний ключ:
    # "на какую сущность ссылается эта запись журнала" (task/time_entry),
    # без реального FK-ограничения в БД (проверяется только на уровне
    # прикладного кода в services/activity_logger.py).
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    activity_type = Column(Enum(ActivityType), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)  # "task", "time_entry", etc.
    entity_id = Column(Integer, nullable=True)  # ID of the affected entity
    description = Column(Text, nullable=False)  # Human-readable description
    activity_metadata = Column(
        JSON, nullable=True
    )  # Additional data (old values, etc.)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )

    # Relationship
    user = relationship("User", back_populates="activity_logs")

    __table_args__ = (
        Index("ix_activity_logs_user_created", "user_id", "created_at"),
        Index("ix_activity_logs_type_created", "activity_type", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<ActivityLog id={self.id} user_id={self.user_id} "
            f"type={self.activity_type} entity={self.entity_type}:{self.entity_id}>"
        )
