"""
Search utilities for full-text search functionality.
"""

import re
import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..schemas import SearchFilters


def normalize_search_query(query: str) -> str:
    """
    Normalize search query by removing extra whitespace and special characters.
    """
    if not query:
        return ""

    # Remove extra whitespace
    query = re.sub(r"\s+", " ", query.strip())

    # Remove special characters that might interfere with PostgreSQL full-text search
    # Keep alphanumeric, spaces, and basic punctuation
    query = re.sub(r"[^\w\s\-@.]", " ", query)

    return query.strip()


def build_search_query(
    query: str, filters: SearchFilters, user_id: int
) -> tuple[str, dict]:
    """
    Build PostgreSQL full-text search query with filters.

    Returns:
        Tuple of (SQL query string, parameters dict)
    """
    # Normalize the search query
    normalized_query = normalize_search_query(query)

    # Base query with full-text search
    sql_parts = [
        "SELECT t.*, ts_rank(to_tsvector('english', t.title || ' ' || COALESCE(t.description, '')), plainto_tsquery('english', :query)) as rank",
        "FROM tasks t",
        "WHERE t.owner_id = :user_id",
        "AND to_tsvector('english', t.title || ' ' || COALESCE(t.description, '')) @@ plainto_tsquery('english', :query)",
    ]

    # Parameters
    params = {"query": normalized_query, "user_id": user_id}

    # Add filters
    filter_conditions = []

    if filters.status is not None:
        filter_conditions.append("t.status = :status")
        params["status"] = filters.status.value

    if filters.category is not None:
        filter_conditions.append("t.category = :category")
        params["category"] = filters.category

    if filters.priority is not None:
        filter_conditions.append("t.priority = :priority")
        params["priority"] = filters.priority.value

    if filters.created_after is not None:
        filter_conditions.append("t.created_at >= :created_after")
        params["created_after"] = filters.created_after

    if filters.created_before is not None:
        filter_conditions.append("t.created_at <= :created_before")
        params["created_before"] = filters.created_before

    if filters.due_after is not None:
        filter_conditions.append("t.due_date >= :due_after")
        params["due_after"] = filters.due_after

    if filters.due_before is not None:
        filter_conditions.append("t.due_date <= :due_before")
        params["due_before"] = filters.due_before

    if filters.archived is not None:
        filter_conditions.append("t.is_archived = :archived")
        params["archived"] = filters.archived

    # Add filter conditions to query
    if filter_conditions:
        sql_parts.extend(filter_conditions)

    # Order by relevance (rank) and then by created_at
    sql_parts.append("ORDER BY rank DESC, t.created_at DESC")

    return " ".join(sql_parts), params


def get_search_suggestions(
    db: Session, user_id: int, partial_query: str, limit: int = 5
) -> list[str]:
    """
    Get search suggestions based on existing task titles and descriptions.
    """
    if not partial_query or len(partial_query) < 2:
        return []

    # Search for tasks that contain the partial query
    suggestions_query = text("""
        SELECT DISTINCT
            CASE
                WHEN LOWER(t.title) LIKE LOWER(:partial || '%') THEN t.title
                WHEN LOWER(t.description) LIKE LOWER(:partial || '%') THEN t.description
                ELSE NULL
            END as suggestion
        FROM tasks t
        WHERE t.owner_id = :user_id
        AND (
            LOWER(t.title) LIKE LOWER(:partial || '%')
            OR LOWER(t.description) LIKE LOWER(:partial || '%')
        )
        AND LENGTH(COALESCE(t.title, '')) > 0
        LIMIT :limit
    """)

    result = db.execute(
        suggestions_query,
        {"partial": partial_query, "user_id": user_id, "limit": limit},
    )

    suggestions = []
    for row in result:
        if row.suggestion and row.suggestion.strip():
            # Extract relevant part (first few words that match)
            suggestion = row.suggestion.strip()
            if len(suggestion) > 50:
                suggestion = suggestion[:47] + "..."
            suggestions.append(suggestion)

    # Remove duplicates and limit
    return list(dict.fromkeys(suggestions))[:limit]


def extract_search_terms(query: str) -> list[str]:
    """
    Extract meaningful search terms from the query for suggestions.
    """
    if not query:
        return []

    # Split by common delimiters and filter out short words
    terms = re.split(r"[\s,.-]+", query.lower())
    return [term.strip() for term in terms if len(term.strip()) >= 2]


def calculate_search_stats(start_time: float, total_matches: int, query: str) -> dict:
    """
    Calculate search performance statistics.
    """
    search_time_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "search_time_ms": search_time_ms,
        "total_matches": total_matches,
        "query_length": len(query),
        "is_complex_query": len(query.split()) > 3,
    }
