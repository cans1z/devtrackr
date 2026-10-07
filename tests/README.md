# Test Configuration

This directory contains the test configuration for the DevTrackr API.

## Setup

1. **Install Dependencies**: Run `pip install -r requirements.txt` to install `python-dotenv`

2. **Environment Variables**: Create a `.env` file in the project root with:
   ```
   TEST_DATABASE_URL=sqlite:///./test.db
   ```

## Configuration (`conftest.py`)

The `conftest.py` file provides:

- **`db_engine`** (session scope): Creates/drops all tables once per test session
- **`db_session`** (function scope): Database session with automatic transaction rollback
- **`client`** (function scope): FastAPI TestClient with overridden database dependency

## Usage

```python
def test_example(client, db_session):
    """Example test using the fixtures."""
    # Use client for HTTP requests
    response = client.get("/")
    assert response.status_code == 200

    # Use db_session for database operations
    # Changes are automatically rolled back after each test
```

## Coverage Reporting

The project includes comprehensive test coverage reporting:

### Running Tests with Coverage
```bash
# Run tests with coverage (default)
python -m pytest

# Run tests in verbose mode
python -m pytest -v

# Run tests with warnings disabled
python -m pytest --disable-warnings

# Generate HTML coverage report
python -m pytest --cov-report=html

# Generate XML coverage report (for CI/CD)
python -m pytest --cov-report=xml

# Check coverage percentage
python -m pytest --cov-report=term-missing
```

### Coverage Reports
- **HTML Report**: Generated in `htmlcov/` directory - open `htmlcov/index.html` in browser
- **Terminal Report**: Shows missing lines in terminal output
- **XML Report**: Generated for CI/CD integration
- **Coverage Threshold**: Tests fail if coverage drops below 80%

## Database Strategy

- Tables created once at session start, dropped at session end
- Each test runs in its own transaction that gets rolled back
- FastAPI's `get_db` dependency is overridden to use test sessions
- Uses SQLite by default for fast test execution
