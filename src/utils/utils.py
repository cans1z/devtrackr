"""
Utility functions for DevTrackr API.

Small helper functions that can be used across the application.
"""

import re
from datetime import UTC, datetime

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def generate_slug(text: str) -> str:
    """
    Generate a URL-friendly slug from text.

    Args:
        text: The text to convert to a slug

    Returns:
        A URL-friendly slug string
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    # Remove special characters except hyphens and alphanumeric
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    # Replace multiple spaces/hyphens with single hyphen
    slug = re.sub(r"[\s-]+", "-", slug)
    # Remove leading/trailing hyphens
    return slug.strip("-")


def format_duration(seconds: int | float) -> str:
    """
    Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2h 30m", "45m", "30s")
    """
    # Normalize and clamp negative durations
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes < 60:
        if remaining_seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {remaining_seconds}s"

    hours = minutes // 60
    remaining_minutes = minutes % 60

    if remaining_minutes == 0:
        return f"{hours}h"
    return f"{hours}h {remaining_minutes}m"


def is_valid_email(email: str) -> bool:
    """
    Simple email validation using regex.

    Args:
        email: Email address to validate

    Returns:
        True if email format is valid, False otherwise
    """
    return EMAIL_PATTERN.fullmatch(email) is not None


def get_current_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format.

    Returns:
        Current timestamp as ISO string
    """
    return datetime.now(UTC).isoformat()


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length with optional suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    # Guard against invalid configuration where max_length is too small
    if max_length <= len(suffix):
        # Best-effort: return a slice of the suffix that fits
        return suffix[:max_length] if max_length > 0 else ""

    return text[: max_length - len(suffix)] + suffix
