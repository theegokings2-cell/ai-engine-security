"""
Pytest configuration and fixtures for Office Manager API tests.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Set up test environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/office_manager_test"
)
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-min-32-chars"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.main import app
from app.db.session import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.tenant import Tenant

# Ensure async fixtures work
pytest_plugins = ("pytest_asyncio",)

# Test database URL
TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
        settings={},
        subscription_tier="enterprise",
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        tenant_id=test_tenant.id,
        email="testuser@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        role="admin",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def auth_token(test_user: User, test_tenant: Tenant) -> str:
    """Create an auth token for the test user."""
    token_data = {
        "sub": str(test_user.id),
        "tenant_id": str(test_tenant.id),
        "role": test_user.role,
        "permissions": [],
    }
    return create_access_token(token_data)


@pytest_asyncio.fixture(scope="function")
async def auth_headers(auth_token: str) -> dict:
    """Return authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database session override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(
    client: AsyncClient,
    auth_headers: dict,
) -> AsyncClient:
    """Create authenticated test client."""
    client.headers.update(auth_headers)
    return client


# Utility fixtures
@pytest.fixture
def sample_customer_data() -> dict:
    """Sample customer data for tests."""
    return {
        "company_name": "Test Company",
        "contact_name": "John Doe",
        "email": "john@testcompany.com",
        "phone": "+1234567890",
        "customer_type": "prospect",
        "industry": "Technology",
    }


@pytest.fixture
def sample_employee_data(test_user: User) -> dict:
    """Sample employee data for tests."""
    return {
        "user_id": str(test_user.id),
        "employee_id": "EMP001",
        "job_title": "Software Engineer",
        "phone": "+1234567890",
    }


@pytest.fixture
def sample_event_data() -> dict:
    """Sample calendar event data for tests."""
    from datetime import datetime, timedelta

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=1)

    return {
        "title": "Test Meeting",
        "description": "A test meeting",
        "event_type": "meeting",
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "location": "Conference Room A",
    }
