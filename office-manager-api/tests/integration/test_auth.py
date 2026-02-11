"""Integration tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    async def test_login_success(
        self, client: AsyncClient, test_user, test_tenant
    ):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser@example.com",
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(
        self, client: AsyncClient, test_user
    ):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "testuser@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401

    async def test_get_current_user(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test getting current user info."""
        response = await authenticated_client.get("/api/v1/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "testuser@example.com"

    async def test_get_current_user_unauthenticated(
        self, client: AsyncClient
    ):
        """Test that /me requires authentication."""
        response = await client.get("/api/v1/auth/me")

        assert response.status_code == 401
