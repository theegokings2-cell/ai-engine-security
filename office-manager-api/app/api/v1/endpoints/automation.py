"""
AI Agent Automation Endpoints
Workflows, agent tasks, and automated actions.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.ai_service import AIService

router = APIRouter(prefix="/automation", tags=["AI Automation"])


def require_admin_or_manager(user: User = Depends(get_current_user)):
    """Require admin or manager role."""
    if user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or manager role required"
        )
    return user


# ============== WORKFLOW TEMPLATES ==============

@router.get("/workflows")
async def list_workflows(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_manager),
):
    """List workflow templates for the tenant."""
    query = select(WorkflowTemplate).where(WorkflowTemplate.tenant_id == user.tenant_id)
    
    if is_active is not None:
        query = query.where(WorkflowTemplate.is_active == is_active)
    
    query = query.offset(skip).limit(limit).order_by(WorkflowTemplate.priority.desc())
    result = await db.execute(query)
    workflows = result.scalars().all()
    
    return {
        "workflows": [
            {
                "id": str(w.id),
                "name": w.name,
                "description": w.description,
                "trigger_type": w.trigger_type,
                "trigger_config": w.trigger_config,
                "is_active": w.is_active,
                "priority": w.priority,
                "created_at": w.created_at.isoformat() if w.created_at else None,
            }
            for w in workflows
        ]
    }


@router.post("/workflows")
async def create_workflow(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    trigger_type: str = Form(...),
    trigger_config: str = Form(...),  # JSON string
    actions: str = Form(...),  # JSON string
    is_active: bool = Form(True),
    priority: int = Form(0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_manager),
):
    """Create a new workflow template."""
    import json
    
    try:
        trigger_cfg = json.loads(trigger_config)
        actions_list = json.loads(actions)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    
    workflow = WorkflowTemplate(
        tenant_id=user.tenant_id,
        name=name,
        description=description,
        trigger_type=trigger_type,
        trigger_config=trigger_cfg,
        actions=actions_list,
        is_active=is_active,
        priority=priority,
        created_by=user.id,
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    
    return {
        "workflow": {
            "id": str(workflow.id),
            "name": workflow.name,
            "trigger_type": workflow.trigger_type,
            "is_active": workflow.is_active,
        },
        "message": "Workflow created successfully"
    }


@router.post("/workflows/{workflow_id}/activate")
async def activate_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_manager),
):
    """Activate a workflow."""
    workflow = await db.get(WorkflowTemplate, UUID(workflow_id))
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    workflow.is_active = True
    await db.commit()
    
    return {"message": "Workflow activated"}


@router.post("/workflows/{workflow_id}/deactivate")
async def deactivate_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin_or_manager),
):
    """Deactivate a workflow."""
    workflow = await db.get(WorkflowTemplate, UUID(workflow_id))
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    workflow.is_active = False
    await db.commit()
    
    return {"message": "Workflow deactivated"}


# ============== AGENT TASKS ==============

@router.get("/agent-tasks")
async def list_agent_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List agent tasks."""
    query = select(AgentTask).where(AgentTask.tenant_id == user.tenant_id)
    
    if status:
        query = query.where(AgentTask.status == status)
    
    if task_type:
        query = query.where(AgentTask.task_type == task_type)
    
    query = query.offset(skip).limit(limit).order_by(AgentTask.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "id": str(t.id),
                "task_type": t.task_type,
                "priority": t.priority,
                "status": t.status,
                "input_data": t.input_data,
                "result": t.result,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ]
    }


@router.post("/agent-tasks")
async def create_agent_task(
    task_type: str = Form(...),
    input_data: str = Form(...),  # JSON string
    instructions: Optional[str] = Form(None),
    priority: str = Form("normal"),
    scheduled_at: Optional[str] = Form(None),  # ISO datetime string
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new agent task for AI processing."""
    import json
    from datetime import datetime
    
    try:
        input_dict = json.loads(input_data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")
    
    scheduled = None
    if scheduled_at:
        try:
            scheduled = datetime.fromisoformat(scheduled_at)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid scheduled_at format")
    
    agent_task = AgentTask(
        tenant_id=user.tenant_id,
        task_type=task_type,
        priority=priority,
        input_data=input_dict,
        instructions=instructions,
        assigned_to_user_id=user.id,
        created_by=user.id,
        scheduled_at=scheduled,
        status="pending" if scheduled else "processing",
    )
    db.add(agent_task)
    await db.commit()
    await db.refresh(agent_task)

    # Process immediately if not scheduled
    if not scheduled:
        try:
            ai_service = AIService(db, str(user.tenant_id))

            if task_type == "summarize":
                text = input_dict.get("text", "")
                if instructions:
                    text = f"Context: {instructions}\n\n{text}"
                result = await ai_service.summarize_content(text)
                agent_task.result = result
                agent_task.status = "completed"
                agent_task.completed_at = datetime.utcnow()

            elif task_type == "follow_up":
                from app.models.office.office_models import Appointment, Customer

                apt_id = input_dict.get("appointment_id")
                channel = input_dict.get("channel", "email")
                if apt_id:
                    appointment = await db.get(Appointment, UUID(apt_id))
                    if appointment:
                        customer_name = "the client"
                        if appointment.customer_id:
                            customer = await db.get(Customer, appointment.customer_id)
                            if customer:
                                customer_name = customer.contact_name or customer.company_name

                        system_prompt = (
                            "You are a professional business assistant that writes follow-up messages "
                            "after appointments. Write concise, warm, and professional messages."
                        )
                        user_prompt = (
                            f"Generate a follow-up message for this appointment:\n"
                            f"- Title: {appointment.title}\n"
                            f"- Customer: {customer_name}\n"
                            f"- Date: {appointment.start_time.isoformat() if appointment.start_time else 'N/A'}\n"
                            f"- Outcome: {appointment.outcome or 'Not recorded'}\n"
                            f"- Next steps: {appointment.next_steps or 'None specified'}\n"
                            f"\nChannel: {channel}"
                        )
                        content = await ai_service._call_llm(system_prompt, user_prompt)
                        agent_task.result = {"content": content, "channel": channel}
                        agent_task.status = "completed"
                        agent_task.completed_at = datetime.utcnow()
                    else:
                        agent_task.status = "failed"
                        agent_task.error_message = "Appointment not found"
                else:
                    agent_task.status = "failed"
                    agent_task.error_message = "appointment_id required in input_data"

            else:
                # Unknown type - leave as pending for future processing
                agent_task.status = "pending"

            await db.commit()
            await db.refresh(agent_task)

        except Exception as e:
            agent_task.status = "failed"
            agent_task.error_message = str(e)
            await db.commit()
            await db.refresh(agent_task)

    return {
        "task": {
            "id": str(agent_task.id),
            "task_type": agent_task.task_type,
            "status": agent_task.status,
            "result": agent_task.result,
        },
        "message": "Agent task created" if agent_task.status == "pending" else f"Agent task {agent_task.status}"
    }


@router.get("/agent-tasks/{task_id}/result")
async def get_agent_task_result(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the result of an agent task."""
    task = await db.get(AgentTask, UUID(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.tenant_id != user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "task": {
            "id": str(task.id),
            "task_type": task.task_type,
            "status": task.status,
            "result": task.result,
            "error_message": task.error_message,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    }


# ============== AI AUTOMATION ENDPOINTS ==============

@router.post("/ai/summarize")
async def summarize_text(
    text: str = Form(...),
    context: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Use AI to summarize text.

    Examples:
    - Summarize meeting notes
    - Summarize customer conversation
    - Summarize document
    """
    try:
        ai_service = AIService(db, str(user.tenant_id))

        if context:
            content = f"Context: {context}\n\n{text}"
        else:
            content = text

        result = await ai_service.summarize_content(content)

        return {
            "summary": result["summary"],
            "action_items": result["action_items"],
            "key_topics": result["key_topics"],
            "sentiment": result["sentiment"],
            "model": "MiniMax-M2.1",
            "input_length": len(text),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )


@router.post("/ai/follow-up")
async def generate_follow_up(
    appointment_id: str = Form(...),
    channel: str = Form("telegram"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate personalized follow-up message for an appointment.
    Uses AI to analyze the appointment and create appropriate follow-up.
    """
    from app.models.office.office_models import Appointment, Customer

    appointment = await db.get(Appointment, UUID(appointment_id))
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if str(appointment.tenant_id) != str(user.tenant_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Load customer name if linked
    customer_name = "the client"
    if appointment.customer_id:
        customer = await db.get(Customer, appointment.customer_id)
        if customer:
            customer_name = customer.contact_name or customer.company_name

    try:
        ai_service = AIService(db, str(user.tenant_id))

        system_prompt = (
            "You are a professional business assistant that writes follow-up messages "
            "after appointments. Write concise, warm, and professional messages. "
            "Adapt the tone for the specified communication channel."
        )

        user_prompt = (
            f"Generate a follow-up message for this appointment:\n"
            f"- Title: {appointment.title}\n"
            f"- Customer: {customer_name}\n"
            f"- Date: {appointment.start_time.isoformat() if appointment.start_time else 'N/A'}\n"
            f"- Type: {appointment.appointment_type}\n"
            f"- Outcome: {appointment.outcome or 'Not recorded'}\n"
            f"- Next steps: {appointment.next_steps or 'None specified'}\n"
            f"\nChannel: {channel}\n"
            f"Write a follow-up message appropriate for {channel}."
        )

        content = await ai_service._call_llm(system_prompt, user_prompt)

        return {
            "message": "Follow-up message generated",
            "channel": channel,
            "content": content,
            "appointment_id": appointment_id,
            "model": "MiniMax-M2.1",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )


@router.post("/ai/task-summary")
async def generate_task_summary(
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate a summary of tasks for a user.
    Useful for daily standups or progress reports.
    """
    from app.models.task import Task

    target_user_id = user_id or str(user.id)

    # Query tasks for the target user
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    pending_query = select(Task).where(
        and_(
            Task.tenant_id == user.tenant_id,
            or_(Task.assignee_id == UUID(target_user_id), Task.creator_id == UUID(target_user_id)),
            Task.status == "pending",
        )
    )
    in_progress_query = select(Task).where(
        and_(
            Task.tenant_id == user.tenant_id,
            or_(Task.assignee_id == UUID(target_user_id), Task.creator_id == UUID(target_user_id)),
            Task.status == "in_progress",
        )
    )
    completed_today_query = select(Task).where(
        and_(
            Task.tenant_id == user.tenant_id,
            or_(Task.assignee_id == UUID(target_user_id), Task.creator_id == UUID(target_user_id)),
            Task.status == "completed",
            Task.completed_at >= today_start,
        )
    )

    pending_result = await db.execute(pending_query)
    in_progress_result = await db.execute(in_progress_query)
    completed_result = await db.execute(completed_today_query)

    pending_tasks = pending_result.scalars().all()
    in_progress_tasks = in_progress_result.scalars().all()
    completed_tasks = completed_result.scalars().all()

    # Build prompt with task data
    task_lines = []
    for t in pending_tasks:
        task_lines.append(f"- [PENDING] {t.title} (priority: {t.priority}, due: {t.due_date.isoformat() if t.due_date else 'no date'})")
    for t in in_progress_tasks:
        task_lines.append(f"- [IN PROGRESS] {t.title} (priority: {t.priority}, due: {t.due_date.isoformat() if t.due_date else 'no date'})")
    for t in completed_tasks:
        task_lines.append(f"- [COMPLETED TODAY] {t.title}")

    if not task_lines:
        return {
            "summary": "No tasks found for this user.",
            "user_id": target_user_id,
            "pending_tasks": 0,
            "in_progress_tasks": 0,
            "completed_today": 0,
        }

    try:
        ai_service = AIService(db, str(user.tenant_id))

        system_prompt = (
            "You are a helpful assistant that generates concise daily task summaries. "
            "Highlight priorities, overdue items, and suggest focus areas."
        )

        user_prompt = (
            f"Generate a daily task summary for this user's tasks:\n\n"
            + "\n".join(task_lines)
            + f"\n\nPending: {len(pending_tasks)}, In Progress: {len(in_progress_tasks)}, Completed Today: {len(completed_tasks)}"
        )

        summary = await ai_service._call_llm(system_prompt, user_prompt)

        return {
            "summary": summary,
            "user_id": target_user_id,
            "pending_tasks": len(pending_tasks),
            "in_progress_tasks": len(in_progress_tasks),
            "completed_today": len(completed_tasks),
            "model": "MiniMax-M2.1",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {str(e)}",
        )


# ============== SIMPLE AUTOMATIONS ==============

@router.post("/remind")
async def send_reminder(
    recipient_id: str = Form(...),
    message: str = Form(...),
    channel: str = Form("telegram"),
    scheduled_for: Optional[str] = Form(None),  # ISO datetime
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Schedule a reminder to be sent.
    Can be sent immediately or scheduled for later.
    """
    from datetime import datetime
    
    scheduled = None
    if scheduled_for:
        try:
            scheduled = datetime.fromisoformat(scheduled_for)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid scheduled_for format")
    
    # Store reminder (would integrate with messaging system)
    
    return {
        "reminder_id": str(uuid4()),
        "message": "Reminder scheduled" if scheduled else "Reminder queued for immediate delivery",
        "scheduled_for": scheduled.isoformat() if scheduled else None,
        "channel": channel,
    }


# Import models at the end to avoid circular imports
from app.models.automation import WorkflowTemplate, WorkflowExecution, AgentTask, AutomationRule
