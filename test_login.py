#!/usr/bin/env python3
"""Test login with test credentials."""
import requests
import json

API_URL = "http://localhost:8000"

def test_login():
    """Test login with test credentials."""
    data = {
        "username": "test@company.com",
        "password": "TestPassword123",
    }

    response = requests.post(
        f"{API_URL}/api/v1/auth/login",
        data=data,
        timeout=10
    )
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

if __name__ == "__main__":
    test_login()
