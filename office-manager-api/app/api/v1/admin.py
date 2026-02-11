"""
Admin API endpoints for tenant management and audit logs.
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.tenant import Tenant
from app.models.audit_log import AuditLog, AuditAction, AuditLogFilter, AuditLogResponse
from app.models.role import Role
from app.core.audit import AuditLogger

router = APIRouter()


# Audit Log Endpoints

@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[AuditAction] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List audit logs for the current tenant.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    # Build query
    query = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action.value)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.created_at >= start_date)
    if end_date:
        query = query.where(AuditLog.created_at <= end_date)
    
    query = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Get user names for response
    user_ids = {log.user_id for log in logs}
    if user_ids:
        users_result = await db.execute(
            select(User.id, User.full_name).where(User.id.in_(user_ids))
        )
        user_names = {str(u.id): u.full_name for u in users_result.all()}
    else:
        user_names = {}
    
    return [
        AuditLogResponse(
            id=str(log.id),
            tenant_id=str(log.tenant_id),
            user_id=str(log.user_id),
            user_name=user_names.get(log.user_id),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=str(log.resource_id) if log.resource_id else None,
            old_values=log.old_values,
            new_values=log.new_values,
            metadata=log.metadata,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]


# Tenant Management Endpoints

@router.get("/tenant")
async def get_tenant_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current tenant information.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    return tenant.to_dict()


@router.put("/tenant/settings")
async def update_tenant_settings(
    settings: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update tenant settings.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    
    # Update settings
    current_settings = tenant.settings or {}
    current_settings.update(settings)
    tenant.settings = current_settings
    
    await db.commit()
    await db.refresh(tenant)
    
    return tenant.to_dict()


# User Management Endpoints (Admin only)

@router.get("/users", response_model=List[dict])
async def list_users(
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users in the tenant.
    Requires admin or manager role.
    """
    if user.role not in [UserRole.ADMIN.value, UserRole.MANAGER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .offset(offset)
        .limit(limit)
    )
    users = result.scalars().all()
    
    return [u.to_dict() for u in users]


@router.get("/users/statistics")
async def get_user_statistics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get user statistics for the tenant.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    # Count users by role
    result = await db.execute(
        select(User.role, func.count(User.id))
        .where(User.tenant_id == tenant_id)
        .group_by(User.role)
    )
    role_counts = dict(result.all())
    
    # Total users
    total_users = sum(role_counts.values())
    
    # Active users
    active_result = await db.execute(
        select(func.count(User.id))
        .where(User.tenant_id == tenant_id, User.is_active == True)
    )
    active_users = active_result.scalar() or 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "by_role": role_counts,
    }


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    new_role: UserRole,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user's role.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    # Get target user
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    old_role = target_user.role
    target_user.role = new_role.value
    
    await db.commit()
    
    # Log permission change
    logger = AuditLogger(db, str(user.id))
    await logger.log(
        action=AuditAction.PERMISSION_CHANGE,
        resource_type="user",
        resource_id=user_id,
        old_values={"role": old_role},
        new_values={"role": new_role.value},
    )
    
    return {"message": f"User role updated to {new_role.value}"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate a user.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    # Get target user
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if str(target_user.id) == str(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )
    
    target_user.is_active = False
    
    await db.commit()
    
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Activate a user.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    target_user.is_active = True
    
    await db.commit()
    
    return {"message": "User activated"}


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(
    user_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle user active status.
    Requires admin role.
    """
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    # Get target user
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == tenant_id,
        )
    )
    target_user = result.scalar_one_or_none()
    
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if str(target_user.id) == str(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot toggle yourself",
        )
    
    target_user.is_active = not target_user.is_active
    
    await db.commit()
    
    status_text = "activated" if target_user.is_active else "deactivated"
    return {"message": f"User {status_text}"}

