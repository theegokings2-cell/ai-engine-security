"""Integration tests for health endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_liveness(self, client: AsyncClient):
        """Test liveness probe returns alive."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Office Manager API"
        assert "version" in data
