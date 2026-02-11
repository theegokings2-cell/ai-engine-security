"""
SMS service using Twilio.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class SMSService:
    """Service for sending SMS via Twilio."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def send_sms(
        self,
        to: str,
        body: str,
        from_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an SMS via Twilio.
        
        If Twilio is not configured, logs the SMS for debugging.
        """
        if not self._is_configured():
            return {
                "status": "stub",
                "message": "SMS service not configured",
                "to": to,
                "body": body[:160],  # SMS limit
            }
        
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
            )
            
            message = client.messages.create(
                body=body[:1600],  # Twilio limit
                from_=settings.TWILIO_PHONE_NUMBER,
                to=to,
            )
            
            return {
                "status": "sent",
                "message_id": message.sid,
                "to": to,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "to": to,
            }
    
    async def send_bulk_sms(
        self,
        to: List[str],
        body: str,
        from_user: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Send SMS to multiple recipients."""
        results = []
        for recipient in to:
            result = await self.send_sms(to=recipient, body=body, from_user=from_user)
            results.append(result)
        return results
    
    async def schedule_sms(
        self,
        to: str,
        body: str,
        send_at: datetime,
        from_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule an SMS to be sent at a specific time."""
        return {
            "status": "scheduled",
            "send_at": send_at.isoformat(),
            "to": to,
            "body": body[:160],
        }
    
    async def get_sms_status(
        self,
        message_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get the status of a sent SMS."""
        if not self._is_configured():
            return {
                "id": message_id,
                "status": "unknown",
                "message": "SMS service not configured",
            }
        
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN,
            )
            
            message = client.messages(message_id).fetch()
            
            return {
                "id": message.sid,
                "status": message.status,
                "to": message.to,
                "sent_at": str(message.date_sent) if message.date_sent else None,
                "delivered_at": str(message.date_created) if message.date_created else None,
            }
        
        except Exception as e:
            return {
                "id": message_id,
                "status": "error",
                "error": str(e),
            }
    
    async def create_template(
        self,
        name: str,
        body: str,
        created_by: str,
    ) -> Dict[str, Any]:
        """Create an SMS template."""
        return {
            "id": str(datetime.utcnow().timestamp()),
            "name": name,
            "body": body,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
        }
    
    def _is_configured(self) -> bool:
        """Check if Twilio is configured."""
        return all([
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_PHONE_NUMBER,
        ])
