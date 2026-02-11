#!/usr/bin/env python3
"""Check available API routes."""
import requests

response = requests.get("http://localhost:8000/openapi.json", timeout=10)
data = response.json()

print("All portal auth routes:")
for path in sorted(data['paths'].keys()):
    if 'portal' in path or 'auth' in path:
        methods = list(data['paths'][path].keys())
        print(f"  {path}: {', '.join(methods)}")
