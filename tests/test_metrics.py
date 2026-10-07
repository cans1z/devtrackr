"""Tests for metrics/analytics endpoints."""

from fastapi import status


class TestMetricsAPI:
    """Tests for /metrics routes."""

    def test_get_summary_empty(self, client):
        """GET /metrics/summary with no tasks returns zero counts."""
        response = client.get("/metrics/summary")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_tasks"] == 0
        assert data["completed_tasks"] == 0
        assert data["in_progress_tasks"] == 0
        assert data["todo_tasks"] == 0
        assert data["completion_rate"] == 0

    def test_get_summary_with_tasks(self, client, db_session):
        """GET /metrics/summary reflects created tasks."""
        client.post("/tasks", json={"title": "Todo 1", "status": "todo"})
        client.post("/tasks", json={"title": "Done 1", "status": "done"})

        response = client.get("/metrics/summary")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_tasks"] == 2
        assert data["todo_tasks"] == 1
        assert data["completed_tasks"] == 1
        assert data["completion_rate"] == 50.0

    def test_get_categories_empty(self, client):
        """GET /metrics/categories with no categorized tasks returns empty list."""
        response = client.get("/metrics/categories")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    def test_get_categories_with_tasks(self, client, db_session):
        """GET /metrics/categories returns breakdown by category."""
        client.post(
            "/tasks",
            json={"title": "Task A", "category": "work", "status": "todo"},
        )
        client.post(
            "/tasks",
            json={"title": "Task B", "category": "work", "status": "done"},
        )
        client.post(
            "/tasks",
            json={"title": "Task C", "category": "personal", "status": "todo"},
        )

        response = client.get("/metrics/categories")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        categories = {c["category"]: c for c in data}
        assert "work" in categories
        assert categories["work"]["count"] == 2
        assert "personal" in categories
        assert categories["personal"]["count"] == 1
