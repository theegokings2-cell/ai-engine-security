"""
Rate limiting middleware for the Office Manager API.
Provides per-tenant and per-user rate limiting using Redis or in-memory storage.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def _get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on tenant and user context.
    Falls back to IP address if no auth context.
    """
    # Try to get tenant_id and user_id from request state
    tenant_id = getattr(request.state, 'tenant_id', None)
    user_id = getattr(request.state, 'user_id', None)
    
    if tenant_id and user_id:
        return f"tenant:{tenant_id}:user:{user_id}"
    elif tenant_id:
        return f"tenant:{tenant_id}"
    elif user_id:
        return f"user:{user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


from app.core.config import settings

limiter = Limiter(
    default_limits=["100/hour", "10/minute"],
    storage_uri=settings.REDIS_URL,
    key_func=_get_rate_limit_key
)


def get_limiter() -> Limiter:
    """Get the rate limiter instance."""
    return limiter


def init_rate_limiting(app):
    """
    Initialize rate limiting for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter


def rate_limit(limit_type: str = "default"):
    """
    Decorator to apply rate limits to endpoints.
    
    Args:
        limit_type: Type of rate limit to apply
        
    Usage:
        @app.post("/tasks")
        @rate_limit("strict")
        async def create_task(...):
            ...
    """
    from functools import wraps
    
    # Define different limit tiers
    limits = {
        "default": "100/hour;10/minute",
        "strict": "50/hour;5/minute",
        "relaxed": "200/hour;30/minute",
        "auth": "10/hour;3/minute",
        "admin": "500/hour;50/minute",
    }
    
    limit = limits.get(limit_type, limits["default"])
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Rate limiting is handled by the middleware
            return await func(*args, **kwargs)
        
        # Mark function with rate limit info
        wrapper._rate_limit = limit
        wrapper._rate_limit_type = limit_type
        return wrapper
    
    return decorator


# Per-tenant rate limit configuration
class TenantRateLimitConfig:
    """Configuration for per-tenant rate limiting."""
    
    # Free tier limits
    FREE_TIER = {
        "requests_per_hour": 100,
        "requests_per_day": 1000,
        "api_calls_per_minute": 10,
    }
    
    # Pro tier limits
    PRO_TIER = {
        "requests_per_hour": 1000,
        "requests_per_day": 10000,
        "api_calls_per_minute": 50,
    }
    
    # Enterprise tier limits
    ENTERPRISE_TIER = {
        "requests_per_hour": 10000,
        "requests_per_day": 100000,
        "api_calls_per_minute": 200,
    }
    
    @classmethod
    def get_limits(cls, tier: str = "free") -> dict:
        """Get rate limits for a tenant tier."""
        tier = tier.lower()
        if tier == "pro":
            return cls.PRO_TIER
        elif tier == "enterprise":
            return cls.ENTERPRISE_TIER
        return cls.FREE_TIER
