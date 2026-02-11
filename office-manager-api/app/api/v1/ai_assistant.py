"""
AI Assistant API - Intelligent command execution for tasks, events, and notes.
"""
from typing import List, Optional, Any, Dict
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_token_from_request, decode_token
from sqlalchemy import select
from app.core.rate_limit import rate_limit
from app.core.audit import AuditLogger
from app.models.user import User
from app.services.ai_service import AIService
from app.services.task_service import TaskService
from app.services.calendar_service import CalendarService

router = APIRouter()


class AICommandRequest(BaseModel):
    """Request to execute an AI command."""
    command: str = Field(..., description="Natural language command to execute")


class CreatedItem(BaseModel):
    """An item created by the AI assistant."""
    type: str  # "task", "event", "note"
    id: str
    title: str
    details: Dict[str, Any] = {}


class AICommandResponse(BaseModel):
    """Response from AI command execution."""
    success: bool
    message: str
    items_created: List[CreatedItem] = []
    ai_response: Optional[str] = None


@router.post("/execute", response_model=AICommandResponse)
@rate_limit("strict")
async def execute_ai_command(
    data: AICommandRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a natural language command using AI.

    The AI assistant can:
    - Create multiple tasks at once
    - Create calendar events/blocks
    - Create task reminders linked to events
    - Understand complex multi-part requests

    Examples:
    - "Create 3 calendar blocks to reach out to sales leads, with task reminders"
    - "Schedule a meeting with John tomorrow at 2pm and create a prep task"
    - "Add tasks for: review budget, send report, call client"
    """
    # Manual authentication since we need the Request object
    token = await get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    tenant_id = get_tenant_from_request(request) or str(user.tenant_id)

    ai_service = AIService(db, tenant_id)
    task_service = TaskService(db, tenant_id)
    calendar_service = CalendarService(db, tenant_id)
    audit_logger = AuditLogger(db, str(user.id), request)

    # Parse the command with AI
    try:
        actions = await ai_service.parse_complex_command(data.command)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse command: {str(e)}"
        )

    items_created: List[CreatedItem] = []

    # Execute each action
    for action in actions:
        try:
            if action["type"] == "task":
                task = await task_service.create_task(
                    task_data={
                        "title": action.get("title", "Untitled Task"),
                        "description": action.get("description", ""),
                        "priority": action.get("priority", "medium"),
                        "due_date": action.get("due_date"),
                        "status": "pending",
                    },
                    created_by_id=str(user.id),
                )
                await audit_logger.create(
                    resource_type="task",
                    resource_id=str(task.id),
                    new_values=task.to_dict(),
                )
                items_created.append(CreatedItem(
                    type="task",
                    id=str(task.id),
                    title=task.title,
                    details={
                        "priority": task.priority.value if hasattr(task.priority, 'value') else task.priority,
                        "due_date": str(task.due_date) if task.due_date else None,
                    }
                ))

            elif action["type"] == "event":
                event = await calendar_service.create_event(
                    event_data={
                        "title": action.get("title", "Untitled Event"),
                        "description": action.get("description", ""),
                        "start_time": action.get("start_time"),
                        "end_time": action.get("end_time"),
                        "event_type": action.get("event_type", "meeting"),
                        "all_day": action.get("all_day", False),
                    },
                    created_by_id=str(user.id),
                )
                await audit_logger.create(
                    resource_type="event",
                    resource_id=str(event.id),
                    new_values={"title": event.title, "start_time": str(event.start_time)},
                )
                items_created.append(CreatedItem(
                    type="event",
                    id=str(event.id),
                    title=event.title,
                    details={
                        "start_time": str(event.start_time) if event.start_time else None,
                        "end_time": str(event.end_time) if event.end_time else None,
                    }
                ))

        except Exception as e:
            # Log but continue with other actions
            print(f"Failed to create {action['type']}: {e}")
            continue

    if not items_created:
        return AICommandResponse(
            success=False,
            message="Could not create any items from your request. Please try rephrasing.",
            items_created=[],
        )

    # Generate summary message
    task_count = sum(1 for i in items_created if i.type == "task")
    event_count = sum(1 for i in items_created if i.type == "event")

    parts = []
    if task_count > 0:
        parts.append(f"{task_count} task{'s' if task_count > 1 else ''}")
    if event_count > 0:
        parts.append(f"{event_count} calendar event{'s' if event_count > 1 else ''}")

    message = f"Created {' and '.join(parts)}"

    return AICommandResponse(
        success=True,
        message=message,
        items_created=items_created,
    )
