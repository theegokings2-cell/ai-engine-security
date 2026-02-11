"""
Email integration API endpoints (Microsoft Graph API).
"""
from typing import List
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.models.user import User
from app.services.email_service import EmailService

router = APIRouter()


class SendEmailRequest(BaseModel):
    """Email send request."""
    to: List[str]
    subject: str
    body: str
    is_html: bool = False


class ScheduleEmailRequest(BaseModel):
    """Email schedule request."""
    to: List[str]
    subject: str
    body: str
    send_at: str  # ISO datetime string
    is_html: bool = False


@router.post("/send")
async def send_email(
    email_data: SendEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send an email via Microsoft Graph API.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = EmailService(db, tenant_id)
    result = await service.send_email(
        to=email_data.to,
        subject=email_data.subject,
        body=email_data.body,
        is_html=email_data.is_html,
        from_user=str(user.id),
    )
    
    return result


@router.post("/schedule")
async def schedule_email(
    email_data: ScheduleEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule an email to be sent at a specific time.
    """
    from datetime import datetime
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    send_at = datetime.fromisoformat(email_data.send_at.replace("Z", "+00:00"))
    
    service = EmailService(db, tenant_id)
    result = await service.schedule_email(
        to=email_data.to,
        subject=email_data.subject,
        body=email_data.body,
        send_at=send_at,
        is_html=email_data.is_html,
        from_user=str(user.id),
    )
    
    return result


@router.get("/status/{email_id}")
async def get_email_status(
    email_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a sent email.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = EmailService(db, tenant_id)
    status = await service.get_email_status(email_id, str(user.id))
    
    return status


@router.post("/templates")
async def create_email_template(
    name: str,
    subject: str,
    body: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an email template for reuse.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = EmailService(db, tenant_id)
    template = await service.create_template(
        name=name,
        subject=subject,
        body=body,
        created_by=str(user.id),
    )
    
    return template


@router.get("/templates")
async def list_email_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all email templates.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = EmailService(db, tenant_id)
    templates = await service.list_templates(str(user.id))
    
    return templates
