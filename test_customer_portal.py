#!/usr/bin/env python3
"""Test customer portal - registration, login, and page access."""
import requests
import json

API_URL = "http://localhost:8000"
BASE_URL = "http://localhost:3000"

def test_customer_portal():
    print("=" * 60)
    print("CUSTOMER PORTAL TEST")
    print("=" * 60)
    
    email = "portaltest@example.com"
    password = "TestPassword123"
    
    # 1. Try to register (or login if already exists)
    print("\n1. Testing Customer Self-Registration/Login...")
    register_data = {
        "email": email,
        "full_name": "Portal Test User",
        "password": password,
        "company_name": "Portal Test Company",
    }
    
    # First try registration
    response = requests.post(
        f"{API_URL}/api/v1/portal/auth/self-register",
        json=register_data,
        timeout=10
    )
    
    if response.status_code == 200:
        print("   [OK] Registration successful!")
        user_data = response.json().get('user', {})
        print(f"   User: {user_data.get('email')}")
    else:
        print(f"   Status: {response.status_code}")
        if "already registered" in response.text.lower():
            print("   User already exists - login will be tested...")
        else:
            print(f"   [FAIL] Registration failed: {response.text[:200]}")
            return
    
    # 2. Now try login
    print("\n2. Testing Login...")
    login_response = requests.post(
        f"{API_URL}/api/v1/portal/auth/login",
        data={"username": email, "password": password},
        timeout=10
    )
    
    if login_response.status_code == 200:
        print("   [OK] Login successful!")
        login_data = login_response.json()
        access_token = login_data.get("access_token")
        print(f"   Token: {access_token[:30]}..." if access_token else "   [WARN] No token!")
    else:
        print(f"   [FAIL] Login failed: {login_response.text[:200]}")
        return
    
    if not access_token:
        print("   [FAIL] No access token received")
        return
    
    # 3. Test protected endpoints with token
    print("\n3. Testing Protected Endpoints...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    endpoints = [
        ("/portal/auth/me", "GET"),
        ("/portal/appointments", "GET"),
        ("/portal/tasks", "GET"),
        ("/portal/notes", "GET"),
        ("/portal/customers", "GET"),
        ("/portal/dashboard/stats", "GET"),
    ]
    
    success_count = 0
    fail_count = 0
    for endpoint, method in endpoints:
        response = requests.get(f"{API_URL}/api/v1{endpoint}", headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"   [OK] {method} {endpoint}: 200")
            success_count += 1
        else:
            print(f"   [FAIL] {method} {endpoint}: {response.status_code}")
            fail_count += 1
    
    # 4. Test automation endpoints
    print("\n4. Testing Automation Endpoints...")
    response = requests.get(f"{API_URL}/api/v1/automation/workflows", headers=headers, timeout=10)
    if response.status_code == 200:
        workflows = response.json()
        count = len(workflows.get('workflows', []))
        print(f"   [OK] GET /automation/workflows: 200 ({count} workflows)")
    else:
        print(f"   [FAIL] GET /automation/workflows: {response.status_code}")
    
    # Summary
    print("\n" + "=" * 60)
    print("CUSTOMER PORTAL TEST COMPLETE")
    print("=" * 60)
    print(f"\nTest Credentials:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"\nFrontend URLs:")
    print(f"   Login: {BASE_URL}/portal/login")
    print(f"   Register: {BASE_URL}/portal/register")
    print(f"   Password Reset: {BASE_URL}/portal/password-reset")
    print(f"   Dashboard: {BASE_URL}/portal/dashboard")
    print(f"\nResults: {success_count} passed, {fail_count} failed")

if __name__ == "__main__":
    test_customer_portal()
