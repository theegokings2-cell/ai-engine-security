"""
Authentication API endpoints.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.core.tenant import TenantContext
from app.db.session import get_db
from app.models.user import User, UserCreate, UserResponse, UserUpdate
from app.models.tenant import Tenant
from app.models.role import Role
from app.models.audit_log import AuditAction
from app.core.audit import log_audit
from app.core.security import get_current_user

from app.core.rate_limit import limiter

router = APIRouter()


@router.post("/register")
@limiter.limit("5/minute;30/hour;100/day")  # Strict rate limiting on registration
async def register(
    request: Request,
    form_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user and tenant.
    The first user becomes the admin of the new tenant.
    """
    # Check if email exists
    existing = await db.execute(
        select(User).where(User.email == form_data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Create tenant
    tenant = Tenant(
        name=form_data.tenant_name if hasattr(form_data, "tenant_name") else form_data.full_name + "'s Company",
        slug=form_data.email.split("@")[0].lower().replace(".", "-"),
        settings={},
        subscription_tier="pro",  # First user gets pro trial
    )
    db.add(tenant)
    await db.flush()
    
    # Create admin user
    user = User(
        tenant_id=tenant.id,
        email=form_data.email,
        hashed_password=get_password_hash(form_data.password),
        full_name=form_data.full_name,
        role="admin",
        is_verified=False,
        phone=form_data.phone,
    )
    db.add(user)
    await db.flush()
    
    # Create default roles if they don't exist
    existing_roles = await db.execute(select(Role.name))
    existing_role_names = {r[0] for r in existing_roles.fetchall()}

    for role_def in Role.get_default_roles():
        if role_def["name"] not in existing_role_names:
            role = Role(**role_def)
            db.add(role)

    await db.commit()
    
    # Generate tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(tenant.id),
            "role": user.role,
            "permissions": [],  # Will be populated from role
        }
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/login")
@limiter.limit("10/minute;100/hour;500/day")  # Stricter limits for auth endpoints
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible login.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    # Set tenant context for audit logging
    TenantContext.set(str(user.tenant_id))
    
    # Generate tokens
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "tenant_id": str(user.tenant_id),
            "role": user.role,
            "permissions": [],  # TODO: Load from role
        }
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)}
    )
    
    # Log login
    await log_audit(
        db=db,
        user_id=str(user.id),
        action=AuditAction.LOGIN,
        resource_type="user",
        resource_id=str(user.id),
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh")
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    """
    from app.core.security import decode_token
    
    try:
        payload = decode_token(refresh_token)
        user_id: str = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        
        # Generate new access token
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "tenant_id": str(user.tenant_id),
                "role": user.role,
                "permissions": [],
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}",
        )


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
):
    """
    Get current user information with permissions.
    """
    user_data = UserResponse.model_validate(user)
    # Add permissions to response
    user_data.permissions = user.get_all_permissions()
    return user_data


@router.put("/me")
async def update_me(
    update_data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile.
    """
    old_values = user.to_dict()
    
    if update_data.full_name:
        user.full_name = update_data.full_name
    if update_data.phone:
        user.phone = update_data.phone
    if update_data.notification_preference:
        user.notification_preference = update_data.notification_preference.value
    if update_data.timezone:
        user.timezone = update_data.timezone
    
    await db.commit()
    await db.refresh(user)
    
    new_values = user.to_dict()
    
    # Log update
    TenantContext.set(str(user.tenant_id))
    await log_audit(
        db=db,
        user_id=str(user.id),
        action=AuditAction.UPDATE,
        resource_type="user",
        resource_id=str(user.id),
        old_values=old_values,
        new_values=new_values,
    )
    
    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change user password.
    """
    from app.core.security import verify_password, get_password_hash
    
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password",
        )
    
    old_values = {"hashed_password": "***"}
    user.hashed_password = get_password_hash(new_password)
    
    await db.commit()
    
    TenantContext.set(str(user.tenant_id))
    await log_audit(
        db=db,
        user_id=str(user.id),
        action=AuditAction.PASSWORD_CHANGE,
        resource_type="user",
        resource_id=str(user.id),
        old_values=old_values,
        new_values={"hashed_password": "***"},
    )
    
    return {"message": "Password changed successfully"}
