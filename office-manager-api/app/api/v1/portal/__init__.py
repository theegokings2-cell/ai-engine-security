"""
Customer Portal Module
Exports for customer-facing portal endpoints
"""
from app.api.v1.portal.auth import router as auth_router
from app.api.v1.portal.dashboard import router as dashboard_router
from app.api.v1.portal.pages import router as pages_router

__all__ = ["auth_router", "dashboard_router", "pages_router"]
