from fastapi import status

from src.models import TimeEntryStatus


class TestTimeTrackingAPI:
    """Tests for the time tracking API endpoints."""

    def test_start_timer(self, client, db_session):
        """Test starting a timer for a task."""
        # First create a task
        task_data = {"title": "Test Task for Timer"}
        response = client.post("/tasks", json=task_data)
        assert response.status_code == status.HTTP_201_CREATED
        task = response.json()
        task_id = task["id"]

        # Start timer
        timer_data = {
            "task_id": task_id,
            "description": "Working on the task",
            "category": "development",
        }
        response = client.post("/time/start", json=timer_data)
        assert response.status_code == status.HTTP_201_CREATED

        time_entry = response.json()
        assert time_entry["task_id"] == task_id
        assert time_entry["description"] == "Working on the task"
        assert time_entry["category"] == "development"
        assert time_entry["status"] == TimeEntryStatus.active
        assert time_entry["start_time"] is not None
        assert time_entry["end_time"] is None
        assert time_entry["duration_minutes"] is None

    def test_get_active_timer(self, client, db_session):
        """Test getting the currently active timer."""
        # Create task and start timer
        task_data = {"title": "Active Timer Task"}
        response = client.post("/tasks", json=task_data)
        task_id = response.json()["id"]

        timer_data = {"task_id": task_id}
        response = client.post("/time/start", json=timer_data)
        assert response.status_code == status.HTTP_201_CREATED
        time_entry_id = response.json()["id"]

        # Get active timer
        response = client.get("/time/active")
        assert response.status_code == status.HTTP_200_OK

        active_timer = response.json()
        assert active_timer is not None
        assert active_timer["time_entry_id"] == time_entry_id
        assert active_timer["task_id"] == task_id
        assert active_timer["task_title"] == "Active Timer Task"
        assert active_timer["start_time"] is not None
        assert active_timer["elapsed_minutes"] >= 0

    def test_stop_timer(self, client, db_session):
        """Test stopping an active timer."""
        # Create task and start timer
        task_data = {"title": "Timer to Stop"}
        response = client.post("/tasks", json=task_data)
        task_id = response.json()["id"]

        timer_data = {"task_id": task_id}
        response = client.post("/time/start", json=timer_data)
        time_entry_id = response.json()["id"]

        # Stop timer
        stop_data = {"description": "Finished working", "category": "testing"}
        response = client.post(f"/time/stop/{time_entry_id}", json=stop_data)
        assert response.status_code == status.HTTP_200_OK

        time_entry = response.json()
        assert time_entry["id"] == time_entry_id
        assert time_entry["status"] == TimeEntryStatus.completed
        assert time_entry["end_time"] is not None
        assert time_entry["duration_minutes"] is not None
        assert time_entry["duration_minutes"] >= 0
        assert time_entry["description"] == "Finished working"
        assert time_entry["category"] == "testing"

    def test_no_active_timer(self, client, db_session):
        """Test getting active timer when none exists."""
        response = client.get("/time/active")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() is None

    def test_cannot_start_multiple_timers(self, client, db_session):
        """Test that user cannot start multiple active timers."""
        # Create two tasks
        task1_data = {"title": "Task 1"}
        task2_data = {"title": "Task 2"}

        response1 = client.post("/tasks", json=task1_data)
        response2 = client.post("/tasks", json=task2_data)

        task1_id = response1.json()["id"]
        task2_id = response2.json()["id"]

        # Start first timer
        timer_data = {"task_id": task1_id}
        response = client.post("/time/start", json=timer_data)
        assert response.status_code == status.HTTP_201_CREATED

        # Try to start second timer
        timer_data = {"task_id": task2_id}
        response = client.post("/time/start", json=timer_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already have an active timer" in response.json()["detail"]

    def test_list_time_entries(self, client, db_session):
        """Test listing time entries."""
        # Create task and add some time entries
        task_data = {"title": "Task with Time Entries"}
        response = client.post("/tasks", json=task_data)
        task_id = response.json()["id"]

        # Start and stop timer
        timer_data = {"task_id": task_id, "category": "development"}
        response = client.post("/time/start", json=timer_data)
        time_entry_id = response.json()["id"]

        response = client.post(f"/time/stop/{time_entry_id}")
        assert response.status_code == status.HTTP_200_OK

        # List time entries
        response = client.get("/time/entries")
        assert response.status_code == status.HTTP_200_OK

        entries = response.json()
        assert len(entries) == 1
        assert entries[0]["task_id"] == task_id
        assert entries[0]["category"] == "development"

    def test_time_summary(self, client, db_session):
        """Test getting time tracking summary."""
        # Create task and add time entry
        task_data = {"title": "Summary Task"}
        response = client.post("/tasks", json=task_data)
        task_id = response.json()["id"]

        # Start and stop timer
        timer_data = {"task_id": task_id, "category": "testing"}
        response = client.post("/time/start", json=timer_data)
        time_entry_id = response.json()["id"]

        response = client.post(f"/time/stop/{time_entry_id}")
        assert response.status_code == status.HTTP_200_OK

        # Get summary
        response = client.get("/time/summary")
        assert response.status_code == status.HTTP_200_OK

        summary = response.json()
        assert summary["total_time_minutes"] >= 0
        assert summary["total_entries"] == 1
        assert summary["average_session_minutes"] >= 0
        assert summary["today_time_minutes"] >= 0
        assert summary["this_week_time_minutes"] >= 0
