"""
SMS integration API endpoints (Twilio).
"""
from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.tenant import get_tenant_from_request
from app.core.security import get_current_user
from app.models.user import User
from app.services.sms_service import SMSService

router = APIRouter()


class SendSMSRequest(BaseModel):
    """SMS send request."""
    to: str  # E.164 format: +1234567890
    body: str


class ScheduleSMSRequest(BaseModel):
    """SMS schedule request."""
    to: str
    body: str
    send_at: str  # ISO datetime string


class BulkSMSRequest(BaseModel):
    """Bulk SMS request."""
    to: list[str]
    body: str


@router.post("/send")
async def send_sms(
    sms_data: SendSMSRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send an SMS via Twilio.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = SMSService(db, tenant_id)
    result = await service.send_sms(
        to=sms_data.to,
        body=sms_data.body,
        from_user=str(user.id),
    )
    
    return result


@router.post("/send-bulk")
async def send_bulk_sms(
    sms_data: BulkSMSRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send SMS to multiple recipients.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = SMSService(db, tenant_id)
    results = await service.send_bulk_sms(
        to=sms_data.to,
        body=sms_data.body,
        from_user=str(user.id),
    )
    
    return {
        "total": len(sms_data.to),
        "sent": len([r for r in results if r["status"] == "sent"]),
        "failed": len([r for r in results if r["status"] == "failed"]),
        "results": results,
    }


@router.post("/schedule")
async def schedule_sms(
    sms_data: ScheduleSMSRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Schedule an SMS to be sent at a specific time.
    """
    from datetime import datetime
    
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    send_at = datetime.fromisoformat(sms_data.send_at.replace("Z", "+00:00"))
    
    service = SMSService(db, tenant_id)
    result = await service.schedule_sms(
        to=sms_data.to,
        body=sms_data.body,
        send_at=send_at,
        from_user=str(user.id),
    )
    
    return result


@router.get("/status/{message_id}")
async def get_sms_status(
    message_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the status of a sent SMS.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = SMSService(db, tenant_id)
    status_result = await service.get_sms_status(message_id, str(user.id))
    
    return status_result


@router.post("/templates")
async def create_sms_template(
    name: str,
    body: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create an SMS template for reuse.
    """
    tenant_id = get_tenant_from_request(None) or str(user.tenant_id)
    
    service = SMSService(db, tenant_id)
    template = await service.create_template(
        name=name,
        body=body,
        created_by=str(user.id),
    )
    
    return template
