# DevTrackr Development Documentation

This document contains comprehensive development information for DevTrackr, including learning progress, API guides, and testing information.

## Table of Contents
- [Learning Progress](#learning-progress)
- [Pagination Guide](#pagination-guide)
- [Search Guide](#search-guide)
- [Testing Summary](#testing-summary)

---

## Learning Progress

This section tracks the development progress and lessons learned while building DevTrackr.

### Day 1 — Project Kickoff
- **Added:** Basic FastAPI app with `/`, `/hello`, and `/time?format=iso|seconds`.
- **Learned:** How to define routes, use `Literal` for query params, and handle UTC time correctly.
- **Challenge:** Confusion over `utcnow()` warning → fixed with `datetime.now(timezone.utc)`.
- **Next:** Add `POST /tasks` with in-memory storage.

### Day 2 — Tasks CRUD Begins
- **Added:** `POST /tasks` to create tasks and `GET /tasks` to list them.
- **Learned:** Using Pydantic models for validation, Gitignore for `.venv`, and FastAPI's automatic 422 errors.
- **Challenge:** Tasks reset on reload (in-memory), JSON escaping in PowerShell was tricky.
- **Next:** Add `GET /tasks/{id}`.

### Day 3 — Database Integration
- **Added:** SQLAlchemy ORM with PostgreSQL, Alembic migrations, and proper database models.
- **Learned:** ORM relationships, database migrations, and proper error handling.
- **Challenge:** Database connection setup and migration management.
- **Next:** Add user authentication and authorization.

### Day 4 — Authentication System
- **Added:** JWT-based authentication with user registration and login.
- **Learned:** Password hashing with bcrypt, JWT token management, and secure API endpoints.
- **Challenge:** Token expiration handling and user session management.
- **Next:** Add task ownership and user-specific endpoints.

### Day 5 — Advanced Features
- **Added:** Task filtering, search functionality, and time tracking capabilities.
- **Learned:** PostgreSQL full-text search, cursor-based pagination, and complex queries.
- **Challenge:** Search performance optimization and pagination consistency.
- **Next:** Add analytics and reporting features.

### Day 6 — Production Ready
- **Added:** Comprehensive testing, Docker containerization, and CI/CD pipeline.
- **Learned:** Production deployment, monitoring, and automated testing.
- **Challenge:** Environment configuration and deployment automation.
- **Next:** Performance optimization and scaling.

---

## Pagination Guide

DevTrackr supports cursor-based pagination for efficient, consistent pagination that works well with large datasets.

### How It Works

Cursor-based pagination uses a "cursor" (encoded token) to mark where the previous page ended, rather than using offset-based pagination. This approach:

- **Prevents duplicate/missing items** when data is added/removed
- **Scales efficiently** with large datasets
- **Maintains consistent ordering** across pages

### API Usage

#### Basic Pagination

```bash
# Get first page (20 items by default)
GET /tasks?limit=20

# Get next page using cursor from previous response
GET /tasks?cursor=eyJpZCI6MTIzfQ==&limit=20

# Get specific page size
GET /tasks?limit=50
```

#### Response Format

```json
{
  "tasks": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTIzfQ==",
    "has_next": true,
    "limit": 20,
    "total_count": 150
  }
}
```

#### Advanced Filtering with Pagination

```bash
# Paginate filtered results
GET /tasks?status=todo&priority=high&limit=10
GET /tasks?status=todo&priority=high&cursor=eyJpZCI6MTIzfQ==&limit=10
```

### Implementation Details

The pagination system uses:
- **Encoded cursors** for security and consistency
- **Database-level ordering** for performance
- **Consistent results** even with concurrent modifications
- **Efficient queries** with proper indexing

---

## Search Guide

DevTrackr includes powerful full-text search capabilities using PostgreSQL's advanced text search features.

### Features

- **Full-text search** across task titles and descriptions
- **Relevance ranking** - most relevant results first
- **Advanced filtering** - combine search with status, category, priority, and date filters
- **Search suggestions** - get suggestions based on existing content
- **Performance optimized** - uses PostgreSQL GIN indexes for fast searches
- **Query normalization** - handles special characters and whitespace

### API Usage

#### Basic Search

```bash
# Simple text search
GET /tasks/search?q=authentication

# Multi-word search
GET /tasks/search?q=user authentication

# Search with special characters
GET /tasks/search?q=API@v2.0
```

#### Advanced Filtering

```bash
# Search with status filter
GET /tasks/search?q=backend&status=todo

# Search with priority filter
GET /tasks/search?q=urgent&priority=urgent

# Search with category filter
GET /tasks/search?q=implementation&category=backend

# Search with date range
GET /tasks/search?q=deadline&due_after=2024-01-01&due_before=2024-12-31
```

#### Combined Filters

```bash
# Complex search with multiple filters
GET /tasks/search?q=backend&status=todo&priority=high&category=backend

# Search with pagination
GET /tasks/search?q=bug&limit=10&cursor=eyJpZCI6MTIzfQ==
```

#### Search Suggestions

```bash
# Get search suggestions
GET /tasks/search?q=doc&include_suggestions=true
```

Response includes:
- Existing task titles matching the query
- Category suggestions
- Priority suggestions

### Search Implementation

The search system uses:
- **PostgreSQL full-text search** with `to_tsvector` and `plainto_tsquery`
- **GIN indexes** for fast text search performance
- **Relevance ranking** with `ts_rank()`
- **Query normalization** to handle special characters
- **Composite indexes** for efficient filtering

### Example Search Query

```sql
SELECT t.*, ts_rank(
    to_tsvector('english', t.title || ' ' || COALESCE(t.description, '')),
    plainto_tsquery('english', :query)
) as rank
FROM tasks t
WHERE t.owner_id = :user_id
AND to_tsvector('english', t.title || ' ' || COALESCE(t.description, ''))
    @@ plainto_tsquery('english', :query)
ORDER BY rank DESC, t.created_at DESC
```

---

## Testing Summary

### Current Testing Status

**Overall Coverage: 77%** (274 statements, 64 missing)

#### Coverage Breakdown by Module

| Module | Statements | Missing | Coverage | Status |
|--------|------------|---------|----------|---------|
| `models.py` | 35 | 0 | **100%** | ✅ Complete |
| `schemas.py` | 75 | 0 | **100%** | ✅ Complete |
| `main.py` | 7 | 1 | **86%** | 🟡 Good |
| `routers/tasks.py` | 88 | 25 | **72%** | 🟡 Good |
| `db.py` | 14 | 6 | **57%** | 🟠 Needs Work |
| `deps.py` | 55 | 32 | **42%** | 🔴 Needs Work |

### Testing Infrastructure

#### Test Framework
- **pytest** - Primary testing framework
- **pytest-cov** - Coverage reporting
- **TestClient** - FastAPI testing client
- **SQLAlchemy** - Database testing with in-memory SQLite

#### Test Structure
```
tests/
├── conftest.py          # Test configuration and fixtures
├── test_tasks_api.py    # Task API endpoint tests
├── test_time_tracking.py # Time tracking tests
└── README.md           # Test documentation
```

#### Key Test Categories

1. **Unit Tests**
   - Model validation
   - Schema serialization
   - Utility functions

2. **Integration Tests**
   - API endpoint functionality
   - Database operations
   - Authentication flows

3. **End-to-End Tests**
   - Complete user workflows
   - Cross-module interactions
   - Error handling

### Running Tests

```bash
# Run all tests
python run_tests.py

# Run specific test file
python -m pytest tests/test_tasks_api.py -v

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Run specific test method
python -m pytest tests/test_tasks_api.py::TestTasksAPI::test_create_task -v
```

### Test Fixtures

- **client** - FastAPI test client
- **db_session** - Database session for testing
- **test_user** - Authenticated user for testing
- **sample_tasks** - Pre-created test data

### Coverage Goals

- **Target**: 90% overall coverage
- **Critical modules**: 95% coverage (auth, core APIs)
- **Utility modules**: 85% coverage

### Areas Needing Attention

1. **Authentication module** (`deps.py`) - 42% coverage
2. **Database module** (`db.py`) - 57% coverage
3. **Error handling** - Edge cases and exception paths
4. **Performance tests** - Load testing for search and pagination

### Test Data Management

- **In-memory SQLite** for fast test execution
- **Fixture-based data** for consistent test state
- **Isolated tests** with proper cleanup
- **Mock external services** for reliable testing

### Continuous Integration

Tests run automatically on:
- **Pull requests** - Full test suite with coverage
- **Main branch** - Extended testing including performance
- **Nightly builds** - Comprehensive test suite with security scanning
