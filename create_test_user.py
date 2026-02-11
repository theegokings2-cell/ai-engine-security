#!/usr/bin/env python3
"""Create a test employee account."""
import requests
import json

API_URL = "http://localhost:8000"

def login_admin():
    """Login as admin to get token."""
    response = requests.post(
        f"{API_URL}/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "password123"},
        timeout=10
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Login failed: {response.status_code}")
        print(response.text)
        return None

def create_test_employee(token):
    """Create test employee with user account."""
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "email": "test@company.com",
        "full_name": "Test Employee",
        "password": "TestPassword123",
        "employee_id": "EMP001",
    }

    response = requests.post(
        f"{API_URL}/api/v1/office/employees/with-user",
        headers=headers,
        data=data,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.status_code == 200

if __name__ == "__main__":
    print("Logging in as admin...")
    token = login_admin()
    if token:
        print("Creating test employee...")
        create_test_employee(token)
    else:
        print("Failed to get admin token")
