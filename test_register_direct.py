#!/usr/bin/env python3
"""Test customer registration directly."""
import requests
import json

API_URL = "http://localhost:8000"

# Test registration with JSON
response = requests.post(
    f"{API_URL}/api/v1/portal/auth/register",
    json={
        "email": "directtest@example.com",
        "full_name": "Direct Test",
        "password": "TestPassword123",
        "company_name": "Direct Test Co",
    },
    timeout=10
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
