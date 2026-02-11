#!/usr/bin/env python3
"""Test employee portal login."""
import requests
import json

API_URL = "http://localhost:8000"

def test_portal_login():
    """Test employee portal login."""
    data = {
        "email": "test@company.com",
        "password": "TestPassword123",
    }

    response = requests.post(
        f"{API_URL}/api/v1/portal/auth/employee-login",
        data=data,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_portal_login()
