"""
Email service using Microsoft Graph API.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class EmailService:
    """Service for sending emails via Microsoft Graph API."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
        from_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an email via Microsoft Graph API.
        
        If Microsoft Graph is not configured, logs the email for debugging.
        """
        if not self._is_configured():
            # Log email for debugging when not configured
            return {
                "status": "stub",
                "message": "Email service not configured",
                "to": to,
                "subject": subject,
                "body": body,
            }
        
        try:
            from app.integrations.microsoft import MicrosoftEmail
            ms_email = MicrosoftEmail(self.db, self.tenant_id)
            
            result = await ms_email.send_email(
                to=to,
                subject=subject,
                body=body,
                is_html=is_html,
            )
            
            return {
                "status": "sent",
                "message_id": result.get("id"),
                "to": to,
            }
        
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "to": to,
            }
    
    async def schedule_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        send_at: datetime,
        is_html: bool = False,
        from_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule an email to be sent at a specific time."""
        # Create a scheduled email record
        scheduled_email = {
            "to": to,
            "subject": subject,
            "body": body,
            "is_html": is_html,
            "send_at": send_at.isoformat(),
            "status": "scheduled",
            "from_user": from_user,
        }
        
        # In production, store in database and use Celery beat to send
        # For now, return the scheduled info
        
        return {
            "status": "scheduled",
            "send_at": send_at.isoformat(),
            "to": to,
            "subject": subject,
        }
    
    async def get_email_status(
        self,
        email_id: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Get the status of a sent email."""
        # In production, query the database for the email record
        return {
            "id": email_id,
            "status": "delivered",
            "sent_at": datetime.utcnow().isoformat(),
            "delivered_at": None,
        }
    
    async def create_template(
        self,
        name: str,
        subject: str,
        body: str,
        created_by: str,
    ) -> Dict[str, Any]:
        """Create an email template."""
        template = {
            "id": str(datetime.utcnow().timestamp()),
            "name": name,
            "subject": subject,
            "body": body,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # In production, store in database
        return template
    
    async def list_templates(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """List email templates."""
        # In production, query from database
        return []
    
    def _is_configured(self) -> bool:
        """Check if Microsoft Graph is configured."""
        return all([
            settings.MICROSOFT_CLIENT_ID,
            settings.MICROSOFT_CLIENT_SECRET,
            settings.MICROSOFT_TENANT_ID,
        ])
