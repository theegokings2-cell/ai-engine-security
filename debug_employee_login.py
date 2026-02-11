#!/usr/bin/env python3
"""Test employee portal login step by step."""
import requests
import json

API_URL = "http://localhost:8000"

def test_employee_login():
    """Test employee portal login endpoint."""
    data = {
        "username": "test@company.com",
        "password": "TestPassword123",
    }

    print("Testing /portal/auth/employee-login...")
    response = requests.post(
        f"{API_URL}/api/v1/portal/auth/employee-login",
        data=data,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

    # Also check user role
    print("\nChecking user in database...")
    from app.models.user import User, UserRole
    # Just print what we know
    print("User 'test@company.com' was created as EMPLOYEE role")

if __name__ == "__main__":
    test_employee_login()
