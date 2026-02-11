"""
Dependencies for FastAPI endpoints.
"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, decode_token
from app.core.tenant import get_tenant_from_request
from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.role import Permission
from app.db.session import get_db


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    return user


async def require_role(required_roles: list[UserRole]):
    """Dependency to require specific roles."""
    async def role_checker(user: User = Depends(get_current_active_user)) -> User:
        if user.role not in [r.value for r in required_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_roles}",
            )
        return user
    return role_checker


async def require_permission(required_permission: Permission):
    """Dependency to require specific permission."""
    async def permission_checker(
        user: User = Depends(get_current_active_user),
    ) -> User:
        # Get permissions from JWT token
        credentials = await get_authorization_header()
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        
        token = credentials.credentials
        payload = decode_token(token)
        permissions = payload.get("permissions", [])
        
        if required_permission.value not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {required_permission.value}",
            )
        
        return user
    return permission_checker


async def get_authorization_header(
    request: Request = None,
    user: User = Depends(get_current_user),
) -> Optional[dict]:
    """Get authorization header (for extracting token info)."""
    return request


async def get_tenant_id(
    request: Request,
    user: User = Depends(get_current_user),
) -> str:
    """Get tenant ID from request or user."""
    tenant_id = get_tenant_from_request(request)
    if tenant_id:
        return tenant_id
    return str(user.tenant_id)


async def get_optional_user(
    credentials = Depends(
        lambda request: request.state.credentials if hasattr(request.state, "credentials") else None
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    if credentials:
        return await get_current_user(credentials, db)
    return None
