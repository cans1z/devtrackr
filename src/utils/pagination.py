"""
Pagination utilities for cursor-based pagination.
"""

import base64
import json
from binascii import Error as BinAsciiError
from datetime import datetime
from typing import Any

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 100


def encode_cursor(data: dict[str, Any]) -> str:
    """Encode cursor data to a base64 string."""
    json_str = json.dumps(data, default=str)
    return base64.b64encode(json_str.encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any] | None:
    """Decode cursor string to data dictionary."""
    try:
        json_str = base64.b64decode(cursor.encode()).decode()
        return json.loads(json_str)
    except (BinAsciiError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def create_task_cursor(task_id: int, created_at: datetime) -> str:
    """Create a cursor for a task based on ID and creation time."""
    return encode_cursor({"id": task_id, "created_at": created_at.isoformat()})


def parse_task_cursor(cursor: str) -> tuple[int | None, datetime | None]:
    """Parse task cursor to extract ID and creation time."""
    data = decode_cursor(cursor)
    if not data:
        return None, None

    task_id = data.get("id")
    created_at_str = data.get("created_at")

    if task_id and created_at_str:
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            return task_id, created_at
        except ValueError:
            pass

    return None, None


def get_pagination_params(
    cursor: str | None = None, limit: int = 20
) -> tuple[int | None, datetime | None, int]:
    """
    Parse pagination parameters.

    Returns:
        Tuple of (cursor_id, cursor_created_at, limit)
    """
    limit = max(MIN_PAGE_SIZE, min(limit, MAX_PAGE_SIZE))

    cursor_id, cursor_created_at = None, None
    if cursor:
        cursor_id, cursor_created_at = parse_task_cursor(cursor)

    return cursor_id, cursor_created_at, limit
