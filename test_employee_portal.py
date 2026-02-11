#!/usr/bin/env python3
"""Test employee portal - login and endpoint access."""
import requests

API_URL = "http://localhost:8000"
BASE_URL = "http://localhost:3000"

def test_employee_portal():
    print("=" * 60)
    print("EMPLOYEE PORTAL TEST")
    print("=" * 60)
    
    email = "test@company.com"
    password = "TestPassword123"
    
    # 1. Test employee login (with employee=true)
    print("\n1. Testing Employee Login...")
    login_response = requests.post(
        f"{API_URL}/api/v1/portal/auth/employee-login",
        data={"username": email, "password": password},
        timeout=10
    )
    print(f"   Status: {login_response.status_code}")
    if login_response.status_code == 200:
        print("   [OK] Employee login successful!")
        access_token = login_response.json().get("access_token")
        print(f"   Token: {access_token[:30]}..." if access_token else "   [WARN] No token!")
    else:
        print(f"   [FAIL] Login failed: {login_response.text[:200]}")
        return
    
    if not access_token:
        print("   [FAIL] No access token received")
        return
    
    # 2. Test employee /me endpoint
    print("\n2. Testing /employee-me endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(
        f"{API_URL}/api/v1/portal/auth/employee-me",
        headers=headers,
        timeout=10
    )
    status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
    print(f"   {status_icon} GET /employee-me: {response.status_code}")
    if response.status_code == 200:
        print(f"   User: {response.json().get('email')}")
    
    # 3. Test protected endpoints
    print("\n3. Testing Protected Endpoints...")
    
    endpoints = [
        ("/portal/auth/me", "GET"),
        ("/portal/appointments", "GET"),
        ("/portal/tasks", "GET"),
        ("/portal/notes", "GET"),
        ("/portal/customers", "GET"),
        ("/portal/dashboard/stats", "GET"),
    ]
    
    for endpoint, method in endpoints:
        response = requests.get(f"{API_URL}/api/v1{endpoint}", headers=headers, timeout=10)
        status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
        print(f"   {status_icon} {method} {endpoint}: {response.status_code}")
    
    # 4. Test regular auth endpoints
    print("\n4. Testing Regular Auth Endpoints...")
    regular_endpoints = [
        ("/api/v1/auth/me", "GET"),
        ("/api/v1/auth/change-password", "POST"),
    ]
    
    for endpoint, method in regular_endpoints:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=10)
        status_icon = "[OK]" if response.status_code == 200 else "[FAIL]"
        print(f"   {status_icon} {method} {endpoint}: {response.status_code}")
    
    print("\n" + "=" * 60)
    print("EMPLOYEE PORTAL TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    test_employee_portal()
