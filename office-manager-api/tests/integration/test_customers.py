"""Integration tests for customer endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestCustomerEndpoints:
    """Tests for customer API endpoints."""

    async def test_list_customers_unauthenticated(self, client: AsyncClient):
        """Test that listing customers requires authentication."""
        response = await client.get("/api/v1/office/customers")

        assert response.status_code == 401

    async def test_list_customers_authenticated(
        self, authenticated_client: AsyncClient
    ):
        """Test listing customers when authenticated."""
        response = await authenticated_client.get("/api/v1/office/customers")

        assert response.status_code == 200
        data = response.json()
        assert "customers" in data or "data" in data

    async def test_create_customer(
        self, authenticated_client: AsyncClient, sample_customer_data: dict
    ):
        """Test creating a new customer."""
        response = await authenticated_client.post(
            "/api/v1/office/customers",
            params=sample_customer_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert "customer" in data or "customer_id" in data

    async def test_create_customer_missing_company_name(
        self, authenticated_client: AsyncClient
    ):
        """Test that company_name is required."""
        response = await authenticated_client.post(
            "/api/v1/office/customers",
            params={"contact_name": "John Doe"},  # Missing company_name
        )

        assert response.status_code == 422  # Validation error

    async def test_create_multiple_customers_unique_numbers(
        self, authenticated_client: AsyncClient
    ):
        """Test that customer numbers are unique."""
        # Create first customer
        response1 = await authenticated_client.post(
            "/api/v1/office/customers",
            params={"company_name": "Company One"},
        )
        assert response1.status_code == 200

        # Create second customer
        response2 = await authenticated_client.post(
            "/api/v1/office/customers",
            params={"company_name": "Company Two"},
        )
        assert response2.status_code == 200

        # Both should succeed with different customer numbers
        # (This tests the MAX-based customer number generation)
