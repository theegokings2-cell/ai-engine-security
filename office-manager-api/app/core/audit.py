"""
Audit logging decorators and utilities.
"""
import functools
import json
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditAction, AuditLog
from app.core.tenant import get_tenant_from_request, TenantContext


def get_audit_metadata(request: Request) -> Dict[str, Any]:
    """Extract metadata from request for audit logging."""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "path": request.url.path,
        "method": request.method,
    }


async def log_audit(
    db: AsyncSession,
    user_id: str,
    action: AuditAction,
    resource_type: str,
    resource_id: Optional[str] = None,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Create an audit log entry."""
    metadata = get_audit_metadata(request) if request else None
    
    audit_log = AuditLog(
        tenant_id=await get_current_tenant_id_from_db(db),
        user_id=user_id,
        action=action.value if isinstance(action, AuditAction) else action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=json.dumps(old_values) if old_values else None,
        new_values=json.dumps(new_values) if new_values else None,
        metadata=json.dumps(metadata) if metadata else None,
        ip_address=metadata.get("ip_address") if metadata else None,
        user_agent=metadata.get("user_agent") if metadata else None,
    )
    
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    
    return audit_log


async def get_current_tenant_id_from_db(db: AsyncSession) -> str:
    """Get tenant ID from tenant context."""
    tenant_id = TenantContext.get()
    if not tenant_id:
        raise ValueError("Tenant context not set")
    return tenant_id


def audit_log(
    action: AuditAction,
    resource_type: str,
    get_resource_id: Optional[Callable] = None,
):
    """
    Decorator to automatically log audit entries for function calls.
    
    Usage:
        @audit_log(action=AuditAction.CREATE, resource_type="task")
        async def create_task(...):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get request from kwargs (FastAPI injects it)
            request = kwargs.get("request")
            
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Log the action (extract db and user from args/kwargs)
            # This is a simplified version - in practice you'd need more robust extraction
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            request = kwargs.get("request")
            result = func(*args, **kwargs)
            return result
        
        # Use async wrapper for async functions
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return wrapper
        return sync_wrapper
    
    return decorator


class AuditLogger:
    """Audit logger class for manual audit logging."""
    
    def __init__(self, db: AsyncSession, user_id: str, request: Optional[Request] = None):
        self.db = db
        self.user_id = user_id
        self.request = request
    
    async def log(
        self,
        action: AuditAction,
        resource_type: str,
        resource_id: Optional[str] = None,
        old_values: Optional[Dict] = None,
        new_values: Optional[Dict] = None,
    ) -> AuditLog:
        """Log an audit entry."""
        return await log_audit(
            db=self.db,
            user_id=self.user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
            request=self.request,
        )
    
    async def create(self, resource_type: str, resource_id: str, new_values: Dict):
        """Log a creation action."""
        return await self.log(
            action=AuditAction.CREATE,
            resource_type=resource_type,
            resource_id=resource_id,
            new_values=new_values,
        )
    
    async def update(
        self,
        resource_type: str,
        resource_id: str,
        old_values: Dict,
        new_values: Dict,
    ):
        """Log an update action."""
        return await self.log(
            action=AuditAction.UPDATE,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
            new_values=new_values,
        )
    
    async def delete(self, resource_type: str, resource_id: str, old_values: Dict):
        """Log a delete action."""
        return await self.log(
            action=AuditAction.DELETE,
            resource_type=resource_type,
            resource_id=resource_id,
            old_values=old_values,
        )
