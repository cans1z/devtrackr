"""
FastAPI dependency injection functions.

Provides database session, authentication, and authorization dependencies.
"""

from collections.abc import Generator
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import SessionLocal
from .security import get_password_hash, verify_password, verify_token

# Для подсветок типов в IDE без загрузки модулей во время исполнения
if TYPE_CHECKING:
    from ..models import Task, User

# JWT token bearer
security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> "User":
    """Get current authenticated user from JWT token."""
    from ..models import User  # <-- Локальный импорт

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    email = verify_token(token)
    if email is None:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: "User" = Depends(get_current_user),
) -> "User":
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_user_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: "User" = Depends(get_current_active_user),
) -> "Task":
    """Get a task by ID and verify it belongs to the current user."""
    from ..models import Task  # <-- Локальный импорт

    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this task"
        )

    return task


# Re-export security functions for convenience
__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_user_task",
    "get_password_hash",
    "verify_password",
]