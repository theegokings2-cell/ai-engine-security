"""
Tests for health check endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app


@pytest.fixture
async def client():
    """Create test client without database dependency."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_liveness_returns_alive(self, client):
        """Test liveness endpoint returns alive status."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"
    
    @pytest.mark.asyncio
    async def test_readiness_checks_database(self, client):
        """Test readiness endpoint validates database connectivity."""
        # Mock the database check to succeed
        with patch('app.main.async_session_factory') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            mock_session.return_value.execute = AsyncMock()
            
            response = await client.get("/health/ready")
            
            # Should return 200 if DB is healthy
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "ok"
    
    @pytest.mark.asyncio
    async def test_readiness_fails_on_db_error(self, client):
        """Test readiness returns 503 when database is unavailable."""
        with patch('app.main.async_session_factory') as mock_session:
            mock_session.return_value.__aenter__ = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            
            response = await client.get("/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["database"] == "error"
    
    @pytest.mark.asyncio
    async def test_celery_health_endpoint(self, client):
        """Test Celery health check returns worker status."""
        with patch('app.main.celery_app') as mock_celery:
            mock_inspect = MagicMock()
            mock_inspect.active.return_value = {
                "worker1": [{"task_id": "abc123"}]
            }
            mock_inspect.stats.return_value = {
                "worker1": {"pool": {"processes": [1, 2, 3, 4]}}
            }
            mock_celery.control.inspect.return_value = mock_inspect
            
            response = await client.get("/health/celery")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "workers" in data
            assert "stats" in data
    
    @pytest.mark.asyncio
    async def test_combined_health_endpoint(self, client):
        """Test combined health endpoint includes all checks."""
        with patch('app.main.async_session_factory') as mock_session, \
             patch('app.main.celery_app') as mock_celery:
            # Mock database
            mock_session.return_value.__aenter__ = AsyncMock()
            mock_session.return_value.__aexit__ = AsyncMock()
            mock_session.return_value.execute = AsyncMock()
            
            # Mock Celery
            mock_inspect = MagicMock()
            mock_inspect.active.return_value = {"worker1": []}
            mock_inspect.stats.return_value = {}
            mock_celery.control.inspect.return_value = mock_inspect
            
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "status" in data
            assert "version" in data
            assert "checks" in data
            assert "database" in data["checks"]
            assert "celery" in data["checks"]
    
    @pytest.mark.asyncio
    async def test_process_time_header(self, client):
        """Test that X-Process-Time header is added to responses."""
        response = await client.get("/health")
        
        assert "X-Process-Time" in response.headers
        
        # Should be a reasonable time (not infinite)
        process_time = float(response.headers["X-Process-Time"])
        assert 0 <= process_time < 10, "Process time should be under 10 seconds"
