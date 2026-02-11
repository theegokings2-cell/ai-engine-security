#!/usr/bin/env python
"""Test script to check office router import."""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from app.api.v1.endpoints.office import router
    print("SUCCESS: Office router imported successfully")
    print(f"Router: {router}")
    print(f"Routes: {[r.path for r in router.routes]}")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
