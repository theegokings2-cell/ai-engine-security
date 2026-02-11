"""
Microsoft Graph API integration for calendar and email.
"""
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class MicrosoftCalendar:
    """Microsoft Graph API for Calendar operations."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    async def _get_access_token(self) -> Optional[str]:
        """Get Microsoft access token using client credentials."""
        if not all([settings.MICROSOFT_CLIENT_ID, settings.MICROSOFT_CLIENT_SECRET]):
            return None
        
        # In production, implement proper OAuth flow
        # This is a simplified placeholder
        return None
    
    async def create_event(self, event) -> Dict[str, Any]:
        """Create an event in Microsoft Calendar."""
        token = await self._get_access_token()
        
        if not token:
            return {
                "id": f"stub-{event.id}",
                "provider": "microsoft",
                "status": "stub",
            }
        
        event_data = {
            "subject": event.title,
            "body": {"contentType": "text", "content": event.description or ""},
            "start": {
                "dateTime": event.start_time.isoformat(),
                "timeZone": event.timezone,
            },
            "end": {
                "dateTime": event.end_time.isoformat(),
                "timeZone": event.timezone,
            },
            "location": {"displayName": event.location} if event.location else None,
            "attendees": [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in event.attendees
            ] if event.attendees else [],
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/me/events",
                json=event_data,
                headers={"Authorization": f"Bearer {token}"},
            )
        
        if response.status_code == 201:
            return {
                "id": response.json()["id"],
                "provider": "microsoft",
                "status": "created",
            }
        
        return {
            "id": None,
            "provider": "microsoft",
            "status": "error",
            "error": response.text,
        }
    
    async def list_events(
        self,
        user_email: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List events from Microsoft Calendar."""
        token = await self._get_access_token()
        
        if not token:
            return []
        
        # Build query params
        params = {}
        if start_date:
            params["$filter"] = f"start/dateTime ge '{start_date}'"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/me/calendarView",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        
        if response.status_code == 200:
            return response.json().get("value", [])
        
        return []
    
    async def sync_events(
        self,
        user_email: str,
        calendar_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Sync events from Microsoft Calendar to local database."""
        events = await self.list_events(user_email)
        
        synced = 0
        for ms_event in events:
            # Map to local event model
            # In production, upsert into local database
            synced += 1
        
        return {
            "synced": synced,
            "provider": "microsoft",
        }


class MicrosoftEmail:
    """Microsoft Graph API for Email operations."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.base_url = "https://graph.microsoft.com/v1.0"
    
    async def _get_access_token(self) -> Optional[str]:
        """Get Microsoft access token."""
        if not all([settings.MICROSOFT_CLIENT_ID, settings.MICROSOFT_CLIENT_SECRET]):
            return None
        return None
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> Dict[str, Any]:
        """Send an email via Microsoft Graph."""
        token = await self._get_access_token()
        
        if not token:
            return {
                "id": f"stub-{datetime.utcnow().timestamp()}",
                "provider": "microsoft",
                "status": "stub",
            }
        
        email_data = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML" if is_html else "Text",
                    "content": body,
                },
                "toRecipients": [
                    {"emailAddress": {"address": email}}
                    for email in to
                ],
            },
            "saveToSentItems": "true",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/me/sendMail",
                json=email_data,
                headers={"Authorization": f"Bearer {token}"},
            )
        
        if response.status_code == 202:
            return {
                "id": response.headers.get("Location", ""),
                "provider": "microsoft",
                "status": "sent",
            }
        
        return {
            "id": None,
            "provider": "microsoft",
            "status": "error",
            "error": response.text,
        }
