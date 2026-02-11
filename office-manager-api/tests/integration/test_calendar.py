"""Integration tests for calendar endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestCalendarEndpoints:
    """Tests for calendar API endpoints."""

    async def test_list_events_unauthenticated(self, client: AsyncClient):
        """Test that listing events requires authentication."""
        response = await client.get("/api/v1/calendar")

        assert response.status_code == 401

    async def test_list_events_authenticated(
        self, authenticated_client: AsyncClient
    ):
        """Test listing events when authenticated."""
        response = await authenticated_client.get("/api/v1/calendar")

        assert response.status_code == 200
        # Response should be a list
        data = response.json()
        assert isinstance(data, list)

    async def test_create_event(
        self, authenticated_client: AsyncClient, sample_event_data: dict
    ):
        """Test creating a new event."""
        response = await authenticated_client.post(
            "/api/v1/calendar",
            json=sample_event_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == sample_event_data["title"]
        assert "id" in data

    async def test_create_event_missing_title(
        self, authenticated_client: AsyncClient
    ):
        """Test that title is required."""
        from datetime import datetime, timedelta

        start = datetime.utcnow() + timedelta(days=1)
        end = start + timedelta(hours=1)

        response = await authenticated_client.post(
            "/api/v1/calendar",
            json={
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
            },
        )

        assert response.status_code == 422  # Validation error

    async def test_get_today_events(
        self, authenticated_client: AsyncClient
    ):
        """Test getting today's events."""
        response = await authenticated_client.get("/api/v1/calendar/today")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
