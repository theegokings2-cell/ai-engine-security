"""
Tenant isolation middleware and context.
"""
from typing import Optional
from fastapi import Request


# Context variable for tenant isolation
class TenantContext:
    """Context manager for tenant isolation."""
    
    _tenant_id: Optional[str] = None
    
    @classmethod
    def set(cls, tenant_id: str) -> None:
        """Set the current tenant ID."""
        cls._tenant_id = tenant_id
    
    @classmethod
    def get(cls) -> Optional[str]:
        """Get the current tenant ID."""
        return cls._tenant_id
    
    @classmethod
    def clear(cls) -> None:
        """Clear the current tenant ID."""
        cls._tenant_id = None


async def get_current_tenant(request: Request) -> Optional[str]:
    """
    Extract tenant_id from JWT token in request Authorization header.
    
    This is called from the middleware to set tenant context for the request.
    """
    from app.core.security import decode_token
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    try:
        token = auth_header.split(" ")[1]
        payload = decode_token(token)
        tenant_id = payload.get("tenant_id")
        
        if tenant_id:
            TenantContext.set(tenant_id)
        
        return tenant_id
    except Exception:
        return None


def get_tenant_from_request(request: Optional[Request]) -> Optional[str]:
    """Get tenant_id from request state (set by middleware)."""
    if request is None:
        return None
    return getattr(request.state, "tenant_id", None)
