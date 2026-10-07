"""
Routes package.

Contains all API route definitions.
"""

from . import activity, auth, metrics, tasks, time_tracking

__all__ = [
    "auth",
    "tasks",
    "metrics",
    "time_tracking",
    "activity",
]
