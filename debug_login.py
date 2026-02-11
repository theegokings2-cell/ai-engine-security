#!/usr/bin/env python3
"""Debug login response."""
import requests

# Test login
login_response = requests.post(
    "http://localhost:8000/api/v1/portal/auth/login",
    data={"username": "portaltest@example.com", "password": "TestPassword123"},
    timeout=10
)
print(f"Login Status: {login_response.status_code}")
print(f"Login Response: {login_response.json()}")

# If successful, test the /me endpoint
if login_response.status_code == 200:
    token = login_response.json().get("access_token")
    print(f"\nToken: {token[:50]}...")
    
    # Test /me endpoint
    headers = {"Authorization": f"Bearer {token}"}
    me_response = requests.get(
        "http://localhost:8000/api/v1/portal/auth/me",
        headers=headers,
        timeout=10
    )
    print(f"\n/me Status: {me_response.status_code}")
    print(f"/me Response: {me_response.json()}")
