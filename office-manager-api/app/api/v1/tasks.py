"""
Task management API endpoints.
"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.core.audit import log_audit, AuditLogger
from app.core.rate_limit import rate_limit
from app.services.task_service import TaskService, MAX_LIMIT, DEFAULT_LIMIT, DEFAULT_OFFSET
from app.models.user import User
from app.models.task import (
    Task,
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskFromText,
    TaskStatus,
)

router = APIRouter()


@router.get("")
@rate_limit("default")
async def list_tasks(
    status_filter: Optional[TaskStatus] = None,
    assignee_id: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(default=DEFAULT_OFFSET, ge=0),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List tasks for the current tenant.
    
    Supports filtering by status, assignee, priority, and search.
    Results are paginated with skip/limit.
    
    Returns:
        - data: List of tasks
        - skip: Number of tasks skipped
        - limit: Maximum tasks returned
        - total: Total count of matching tasks
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    tasks, total = await service.list_tasks(
        status_filter=status_filter,
        assignee_id=assignee_id,
        priority=priority,
        search=search,
        limit=limit,
        offset=skip,
        user_id=str(user.id) if user.role == "employee" else None,
    )
    
    return {
        "data": tasks,
        "skip": skip,
        "limit": limit,
        "total": total,
        "has_more": (skip + len(tasks)) < total,
    }


@router.get("/statistics")
@rate_limit("default")
async def get_task_statistics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get task statistics for the current tenant.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    stats = await service.get_statistics(
        user_id=str(user.id) if user.role == "employee" else None
    )
    
    return stats


@router.get("/{task_id}", response_model=TaskResponse)
@rate_limit("default")
async def get_task(
    task_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific task by ID.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    task = await service.get_task(task_id, str(user.id), user.role)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return task


@router.post("", response_model=TaskResponse)
@rate_limit("strict")
async def create_task(
    task_data: TaskCreate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new task.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    task = await service.create_task(
        task_data=task_data.model_dump(),
        created_by_id=str(user.id),
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.create(
        resource_type="task",
        resource_id=str(task.id),
        new_values=task.to_dict(),
    )
    
    return task


@router.post("/from-text", response_model=TaskResponse)
@rate_limit("strict")
async def create_task_from_text(
    data: TaskFromText,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a task from natural language text.
    
    Example:
    ```
    POST /api/v1/tasks/from-text
    {
        "text": "remind finance to approve Acme invoice tomorrow at 3pm"
    }
    ```
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    task = await service.create_from_natural_language(
        text=data.text,
        created_by_id=str(user.id),
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.create(
        resource_type="task",
        resource_id=str(task.id),
        new_values=task.to_dict(),
    )
    
    return task


@router.put("/{task_id}", response_model=TaskResponse)
@rate_limit("default")
async def update_task(
    task_id: str,
    task_data: TaskUpdate,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing task.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    # Get old values for audit
    service = TaskService(db, tenant_id)
    old_task = await service.get_task(task_id, str(user.id), user.role)
    
    if not old_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    old_values = old_task.to_dict()
    
    # Update
    task = await service.update_task(
        task_id=task_id,
        task_data=task_data.model_dump(exclude_unset=True),
        user_id=str(user.id),
        user_role=user.role,
    )
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.update(
        resource_type="task",
        resource_id=task_id,
        old_values=old_values,
        new_values=task.to_dict(),
    )
    
    return task


@router.post("/{task_id}/complete")
@rate_limit("default")
async def complete_task(
    task_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a task as completed.
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    service = TaskService(db, tenant_id)
    task = await service.complete_task(
        task_id=task_id,
        user_id=str(user.id),
        user_role=user.role,
    )
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    return task


@router.delete("/{task_id}")
@rate_limit("default")
async def delete_task(
    task_id: str,
    request: Request = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a task (soft delete).
    """
    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)
    
    # Get old values for audit
    service = TaskService(db, tenant_id)
    old_task = await service.get_task(task_id, str(user.id), user.role)
    
    if not old_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
    
    await service.delete_task(task_id, str(user.id), user.role)
    
    # Log audit
    logger = AuditLogger(db, str(user.id), request)
    await logger.delete(
        resource_type="task",
        resource_id=task_id,
        old_values=old_task.to_dict(),
    )
    
    return {"message": "Task deleted successfully"}
