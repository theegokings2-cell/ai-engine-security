#!/usr/bin/env python3
"""Debug notes endpoint."""
import requests

# Login as employee
login_response = requests.post(
    "http://localhost:8000/api/v1/portal/auth/employee-login",
    data={"username": "test@company.com", "password": "TestPassword123"},
    timeout=10
)
print(f"Login: {login_response.status_code}")

token = login_response.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Test notes endpoint
response = requests.get(
    "http://localhost:8000/api/v1/portal/notes",
    headers=headers,
    timeout=10
)
print(f"Notes: {response.status_code}")
print(f"Response: {response.text[:500]}")
