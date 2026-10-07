"""
Utilities package.

Contains helper functions and utilities used across the application.
"""

from .pagination import (
    create_task_cursor,
    decode_cursor,
    encode_cursor,
    get_pagination_params,
    parse_task_cursor,
)
from .search_utils import (
    build_search_query,
    calculate_search_stats,
    extract_search_terms,
    get_search_suggestions,
    normalize_search_query,
)
from .utils import (
    format_duration,
    generate_slug,
    get_current_timestamp,
    is_valid_email,
    truncate_string,
)

__all__ = [
    # Pagination
    "encode_cursor",
    "decode_cursor",
    "create_task_cursor",
    "parse_task_cursor",
    "get_pagination_params",
    # Search
    "normalize_search_query",
    "build_search_query",
    "get_search_suggestions",
    "extract_search_terms",
    "calculate_search_stats",
    # Utils
    "generate_slug",
    "format_duration",
    "is_valid_email",
    "get_current_timestamp",
    "truncate_string",
]
