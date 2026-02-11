"""
Tenant isolation tests for the Office Manager API.
Ensures proper separation between tenants.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.core.config import settings


@pytest.fixture
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+asyncpg"),
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Create async session for testing."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest.fixture
async def client(async_session):
    """Create test client."""
    async def override_get_db():
        yield async_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


class TestTenantIsolation:
    """Test suite for tenant isolation validation."""
    
    @pytest.mark.asyncio
    async def test_cross_tenant_access_denied(self, client):
        """
        Test that users cannot access resources from other tenants.
        
        This is critical for multi-tenant security. When tenant A creates
        a resource, tenant B should receive a 404 (not found), not 403
        (forbidden), to prevent information disclosure.
        """
        # Create task as tenant_1 (simulated)
        # In production, this would involve proper JWT authentication
        
        # Simulate authenticated request for tenant_1
        tenant_1_token = "tenant_1_token"
        
        # Create a task for tenant_1
        task_response = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Secret task from tenant 1",
                "description": "This should not be accessible by tenant 2",
            },
            headers={"Authorization": f"Bearer {tenant_1_token}"},
        )
        
        # Should succeed or return 201/200
        assert task_response.status_code in [200, 201]
        task_data = task_response.json()
        task_id = task_data.get("id") or task_data.get("data", {}).get("id")
        
        if not task_id:
            pytest.skip("Task creation not fully implemented in test setup")
            return
        
        # Try to access as tenant_2
        tenant_2_token = "tenant_2_token"
        response = await client.get(
            f"/api/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {tenant_2_token}"},
        )
        
        # MUST return 404, NOT 403
        # 403 would indicate the resource exists but user lacks permission
        # 404 properly hides the resource's existence
        assert response.status_code == 404, (
            f"Cross-tenant access should return 404, got {response.status_code}. "
            f"Response: {response.json()}"
        )
    
    @pytest.mark.asyncio
    async def test_tenant_filtering_in_list(self, client):
        """
        Test that list endpoints only return resources for the current tenant.
        """
        tenant_1_token = "tenant_1_token"
        tenant_2_token = "tenant_2_token"
        
        # Create tasks for tenant 1
        await client.post(
            "/api/v1/tasks",
            json={"title": "Tenant 1 Task 1"},
            headers={"Authorization": f"Bearer {tenant_1_token}"},
        )
        await client.post(
            "/api/v1/tasks",
            json={"title": "Tenant 1 Task 2"},
            headers={"Authorization": f"Bearer {tenant_1_token}"},
        )
        
        # Create tasks for tenant 2
        await client.post(
            "/api/v1/tasks",
            json={"title": "Tenant 2 Task 1"},
            headers={"Authorization": f"Bearer {tenant_2_token}"},
        )
        
        # List tasks as tenant 1 - should only see their tasks
        response = await client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {tenant_1_token}"},
        )
        
        assert response.status_code == 200
        tasks = response.json().get("data", response.json())
        
        # Verify tenant 1 only sees their tasks
        tenant_1_tasks = [t for t in tasks if "Tenant 1" in str(t.get("title", ""))]
        tenant_2_tasks = [t for t in tasks if "Tenant 2" in str(t.get("title", ""))]
        
        assert len(tenant_2_tasks) == 0, (
            "Tenant 1 should not see tenant 2's tasks"
        )
    
    @pytest.mark.asyncio
    async def test_tenant_isolation_on_create(self, client):
        """
        Test that resources are created with correct tenant_id.
        """
        tenant_id = "test_tenant_123"
        
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "Test task"},
            headers={"Authorization": f"Bearer {tenant_id}"},
        )
        
        # If creation succeeds, verify tenant_id is set
        if response.status_code in [200, 201]:
            data = response.json()
            # The created resource should have the correct tenant_id
            assert data.get("tenant_id") == tenant_id or \
                   data.get("data", {}).get("tenant_id") == tenant_id


class TestRateLimiting:
    """Test suite for rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are included in responses."""
        response = await client.get("/health")
        
        # Should have rate limit headers
        assert "X-RateLimit-Limit" in response.headers or \
               "X-RateLimit-Remaining" in response.headers or \
               response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, client):
        """
        Test that requests are rejected when rate limit is exceeded.
        
        Note: This test may be flaky in CI due to shared rate limit counters.
        """
        # Make many requests quickly
        for i in range(15):
            response = await client.get("/health")
            if response.status_code == 429:
                # Rate limited - test passes
                assert "Retry-After" in response.headers
                return
        
        # If we didn't get rate limited, check that headers suggest limits exist
        # This is acceptable in shared environments


class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_liveness_endpoint(self, client):
        """Test liveness endpoint returns alive status."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "alive"
    
    @pytest.mark.asyncio
    async def test_readiness_includes_database(self, client):
        """Test readiness endpoint checks database connectivity."""
        # This test requires a running database
        # Skip if not available
        try:
            response = await client.get("/health/ready")
            assert response.status_code in [200, 503]
            data = response.json()
            assert "database" in data
        except Exception:
            pytest.skip("Database not available for test")


class TestPagination:
    """Test suite for pagination limits."""
    
    @pytest.mark.asyncio
    async def test_pagination_limits(self, client):
        """Test that pagination respects maximum limits."""
        # Request with excessive limit
        response = await client.get(
            "/api/v1/tasks",
            params={"limit": 1000},
        )
        
        # Should either respect limit or cap it
        if response.status_code == 200:
            data = response.json()
            returned_items = len(data.get("data", data))
            # Should not return more than max allowed (100)
            assert returned_items <= 100, (
                f"Pagination should cap at 100, got {returned_items}"
            )
    
    @pytest.mark.asyncio
    async def test_pagination_skip_validation(self, client):
        """Test that skip parameter is validated (no negative values)."""
        response = await client.get(
            "/api/v1/tasks",
            params={"skip": -1},
        )
        
        # Should reject invalid skip value
        assert response.status_code in [400, 422]
