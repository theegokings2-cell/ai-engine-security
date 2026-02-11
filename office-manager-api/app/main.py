"""
Office Manager API - Main Application Entry Point
"""
import time
import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

# Import all models FIRST to register SQLAlchemy relationships before any API modules
import app.models  # noqa: F401
# Models imported successfully

from app.api.v1 import auth, calendar, tasks, notes, email, sms, admin, admin_ui, portal, ai_assistant
from app.api.v1.endpoints.office import router as office_router
from app.api.v1.endpoints.portal import router as portal_endpoints_router
from app.api.v1.endpoints.portal.auth import router as portal_auth_endpoints_router
from app.api.v1.endpoints.automation import router as automation_router
from app.integrations.telegram import router as telegram_router
from app.core.config import settings
from app.core.tenant import TenantContext, get_current_tenant
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import limiter, init_rate_limiting
from app.core.http_client import http_client
from app.db.session import engine, async_session_factory
from app.core.celery_app import celery_app

# Initialize logging
setup_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler."""
    # Startup
    logger.info("application_starting", version="1.0.0", env=settings.APP_ENV)
    
    # 🚨 CRITICAL SECURITY VALIDATION: JWT secret must be set
    if not settings.JWT_SECRET_KEY or settings.JWT_SECRET_KEY.startswith("generate-"):
        raise RuntimeError(
            "CRITICAL: JWT_SECRET_KEY is not set or uses default value! "
            "Set a strong secret in environment variables before starting the app. "
            "Run: python -c \"import secrets; print(secrets.token_hex(32))\""  # noqa: T201
        )
    
    # 🚨 CRITICAL SECURITY VALIDATION: SECRET_KEY must be set
    if not settings.SECRET_KEY or settings.SECRET_KEY.startswith("change-this-"):
        raise RuntimeError(
            "CRITICAL: SECRET_KEY is not set or uses default value! "
            "Set a strong secret in environment variables before starting the app."
        )
    
    # Initialize database tables
    from app.db.session import init_db
    try:
        await init_db()
        logger.info("database_tables_created")
    except Exception as e:
        logger.error("db_init_failed", error=str(e))
    
    # TODO: Re-enable seed code after bcrypt/passlib Python 3.14 fix
    # Seed default admin user and roles
    # try:
    #     from sqlalchemy import text
    #     async with async_session_factory() as session:
    #         result = await session.execute(text("SELECT COUNT(*) FROM users"))
    #         user_count = result.scalar()
    #         
    #         if user_count == 0:
    #             logger.info("seeding_default_data")
    #             from app.core.security import get_password_hash
    #             from app.models.tenant import Tenant, TenantSettings
    #             from app.models.user import User
    #             from app.models.role import Role
    #             from uuid import uuid4
    #             
    #             tenant = Tenant(
    #                 id=uuid4(),
    #                 name="Default Organization",
    #                 slug="default-org",
    #                 settings=TenantSettings().model_dump(),
    #                 subscription_tier="enterprise",
    #             )
    #             session.add(tenant)
    #             await session.flush()
    #             
    #             admin_user = User(
    #                 id=uuid4(),
    #                 tenant_id=tenant.id,
    #                 email="admin@example.com",
    #                 hashed_password=get_password_hash("password123"),
    #                 full_name="Admin User",
    #                 role="admin",
    #                 is_active=True,
    #                 is_verified=True,
    #             )
    #             session.add(admin_user)
    #             
    #             for role_def in Role.get_default_roles():
    #                 role = Role(**role_def)
    #                 session.add(role)
    #             
    #             await session.commit()
    #             logger.info("default_admin_created", email="admin@example.com")
    #         else:
    #             logger.info("users_exist", count=user_count)
    # except Exception as e:
    #     logger.error("seed_failed", error=str(e), traceback=traceback.format_exc())
    
    yield
    # Shutdown
    logger.info("application_shutting_down")
    await http_client.close()
    await engine.dispose()


app = FastAPI(
    title="Office Manager API",
    description="AI-powered Office Management SaaS Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Initialize rate limiting
init_rate_limiting(app)

# CORS middleware
# Note: When allow_credentials=True, allow_origins cannot be "*"
# Must specify explicit origins for credential-based requests
cors_origins = [
    "http://localhost:3000",  # Next.js dev server
    "http://127.0.0.1:3000",
    "http://localhost:8000",  # API docs
    "http://127.0.0.1:8000",
]
# Add configured frontend URL if set
if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
    cors_origins.append(settings.FRONTEND_URL)

logger.debug("cors_origins_configured", origins=cors_origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    
    # Only add headers to API responses, not static files
    if request.url.path.startswith("/api") or request.url.path.startswith("/"):
        # Prevent XSS attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (restrictive for production, looser for dev)
        if settings.APP_ENV == "production":
            response.headers["Content-Security-Policy"] = "default-src 'self'"
        else:
            response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval'"
        
        # Strict Transport Security (HTTPS only) - enable in production!
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (disable features that could leak info)
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    
    return response


# Request middleware for tenant isolation and request timing
@app.middleware("http")
async def request_middleware(request: Request, call_next):
    """Extract tenant_id from JWT and set in request state."""
    start_time = time.time()
    
    # Skip for public endpoints
    if request.url.path.startswith("/api/v1/auth/register"):
        response = await call_next(request)
        response.headers["X-Process-Time"] = str(time.time() - start_time)
        return response
    
    if request.url.path.startswith("/health") or request.url.path.startswith("/docs"):
        response = await call_next(request)
        response.headers["X-Process-Time"] = str(time.time() - start_time)
        return response
    
    try:
        tenant_id = await get_current_tenant(request)
        if tenant_id:
            request.state.tenant_id = tenant_id
    except Exception:
        pass
    
    response = await call_next(request)
    response.headers["X-Process-Time"] = str(time.time() - start_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and log them."""
    logger.error("exception_handler_caught", error_type=type(exc).__name__, error=str(exc))
    request_id = getattr(request.state, 'request_id', 'unknown')
    tenant_id = getattr(request.state, 'tenant_id', 'unknown')
    user_id = getattr(request.state, 'user_id', 'unknown')
    
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=user_id,
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
    )
    
    # Don't expose internal details in production
    if settings.APP_ENV == "production":
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal error occurred",
                "request_id": request_id,
            },
        )
    else:
        # Show details for debugging in development
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "request_id": request_id,
                "type": type(exc).__name__,
                "traceback": traceback.format_exc(),
            },
        )


# Include API routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(calendar.router, prefix="/api/v1/calendar", tags=["Calendar"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(notes.router, prefix="/api/v1/notes", tags=["Notes"])
app.include_router(email.router, prefix="/api/v1/email", tags=["Email"])
app.include_router(sms.router, prefix="/api/v1/sms", tags=["SMS"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(ai_assistant.router, prefix="/api/v1/ai", tags=["AI Assistant"])
app.include_router(office_router, prefix="/api/v1/office", tags=["Office Management"])

# Telegram integration
app.include_router(telegram_router)

# Customer Portal routes (HTML templates)
app.include_router(portal.pages.router)

# Customer Portal API routes (routers already have /portal/... prefix)
app.include_router(portal.auth.router, prefix="/api/v1", tags=["Customer Portal Auth"])
# portal.dashboard.router disabled — replaced by portal_endpoints_router /portal/dashboard/stats
app.include_router(portal_endpoints_router, prefix="/api/v1", tags=["Portal API"])
app.include_router(portal_auth_endpoints_router, prefix="/api/v1", tags=["Portal Auth Endpoints"])

# AI Automation routes (router already has /automation prefix)
app.include_router(automation_router, prefix="/api/v1", tags=["AI Automation"])

# Admin UI routes (HTML templates)
app.include_router(admin_ui.router)


# Health check endpoints
@app.get("/health/live", tags=["Health"])
def liveness():
    """Liveness probe - indicates if the app is running."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness():
    """Readiness probe - indicates if the app is ready to serve traffic."""
    from sqlalchemy import text
    # Check database connectivity
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("health_check_db_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error", "error": str(e)},
        )
    
    return {"status": "ready", "database": db_status}


@app.get("/health/celery", tags=["Health"])
def celery_health():
    """Check Celery worker health."""
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        stats = inspect.stats()
        
        # Check if any workers are active
        workers_healthy = active is not None and len(active) > 0
        
        return {
            "status": "healthy" if workers_healthy else "degraded",
            "workers": active or {},
            "stats": stats or {},
            "worker_count": len(active) if active else 0,
        }
    except Exception as e:
        logger.error("health_check_celery_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={"status": "error", "celery": "unavailable", "error": str(e)},
        )


@app.get("/health", tags=["Health"])
async def health_check():
    """Combined health check endpoint."""
    from sqlalchemy import text
    db_status = "ok"
    celery_status = "unknown"
    
    # Check database
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Celery
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        celery_status = "healthy" if active else "no_workers"
    except Exception as e:
        celery_status = f"error: {str(e)}"
    
    overall_status = "healthy" if db_status == "ok" and celery_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "checks": {
            "database": db_status,
            "celery": celery_status,
        },
    }


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Office Manager API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
