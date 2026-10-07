"""Tests for authentication endpoints."""

from fastapi import status


class TestAuthAPI:
    """Tests for /auth routes."""

    def test_get_me(self, client):
        """GET /auth/me returns the authenticated user."""
        response = client.get("/auth/me")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["username"] == "testuser"
        assert "id" in data
        assert data.get("is_active") is True
        assert "created_at" in data

    def test_login_success(self, client):
        """POST /auth/login with valid credentials returns a token."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_invalid_password(self, client):
        """POST /auth/login with wrong password returns 401."""
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()

    def test_login_unknown_email(self, client):
        """POST /auth/login with unknown email returns 401."""
        response = client.post(
            "/auth/login",
            json={"email": "unknown@example.com", "password": "testpassword123"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_register_success(self, client, db_session):
        """POST /auth/register creates a new user."""
        response = client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "securepass123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    def test_register_duplicate_email(self, client):
        """POST /auth/register with existing email returns 400."""
        response = client.post(
            "/auth/register",
            json={
                "email": "test@example.com",
                "username": "othername",
                "password": "securepass123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json().get("detail", "").lower()

    def test_register_duplicate_username(self, client):
        """POST /auth/register with existing username returns 400."""
        response = client.post(
            "/auth/register",
            json={
                "email": "other@example.com",
                "username": "testuser",
                "password": "securepass123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.json().get("detail", "").lower()
