"""
Calendar service for event management.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventType


class CalendarService:
    """Service for calendar operations."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def list_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[EventType] = None,
        limit: int = 100,
        offset: int = 0,
        user_id: Optional[str] = None,
    ) -> List[Event]:
        """List events with optional filters."""
        query = select(Event).where(Event.tenant_id == self.tenant_id)
        
        if start_date:
            query = query.where(Event.start_time >= start_date)
        if end_date:
            query = query.where(Event.end_time <= end_date)
        if event_type:
            query = query.where(Event.event_type == event_type.value)
        
        query = query.order_by(Event.start_time.asc()).offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_event(
        self,
        event_id: str,
        user_id: str,
    ) -> Optional[Event]:
        """Get a specific event by ID."""
        result = await self.db.execute(
            select(Event).where(
                Event.id == event_id,
                Event.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_today_events(
        self,
        user_id: str,
    ) -> Dict[str, List[Event]]:
        """Get today's events grouped by time."""
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        result = await self.db.execute(
            select(Event)
            .where(
                and_(
                    Event.tenant_id == self.tenant_id,
                    Event.start_time >= today,
                    Event.start_time < tomorrow,
                )
            )
            .order_by(Event.start_time.asc())
        )
        events = result.scalars().all()
        
        # Group by hour
        grouped = {}
        for event in events:
            hour = event.start_time.hour
            if hour not in grouped:
                grouped[hour] = []
            grouped[hour].append(event)
        
        return {
            "date": today.isoformat(),
            "events_by_hour": grouped,
            "total_count": len(events),
        }
    
    async def create_event(
        self,
        event_data: Dict[str, Any],
        created_by_id: str,
    ) -> Event:
        """Create a new calendar event."""
        event = Event(
            tenant_id=self.tenant_id,
            title=event_data.get("title"),
            description=event_data.get("description"),
            event_type=event_data.get("event_type", EventType.MEETING.value),
            start_time=event_data.get("start_time"),
            end_time=event_data.get("end_time"),
            all_day="Y" if event_data.get("all_day", False) else "N",
            timezone=event_data.get("timezone", "UTC"),
            location=event_data.get("location"),
            attendees=event_data.get("attendees", []),
            reminder_minutes=event_data.get("reminder_minutes", [15, 60]),
            created_by_id=created_by_id,
        )
        
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)

        # Schedule reminders
        await self._schedule_reminders(event)

        return event
    
    async def update_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
        user_id: str,
    ) -> Optional[Event]:
        """Update an existing event."""
        result = await self.db.execute(
            select(Event).where(
                Event.id == event_id,
                Event.tenant_id == self.tenant_id,
            )
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return None
        
        # Update fields
        if "title" in event_data:
            event.title = event_data["title"]
        if "description" in event_data:
            event.description = event_data["description"]
        if "event_type" in event_data:
            event.event_type = event_data["event_type"]
        if "start_time" in event_data:
            event.start_time = event_data["start_time"]
        if "end_time" in event_data:
            event.end_time = event_data["end_time"]
        if "all_day" in event_data:
            event.all_day = "Y" if event_data["all_day"] else "N"
        if "location" in event_data:
            event.location = event_data["location"]
        if "attendees" in event_data:
            event.attendees = event_data["attendees"]
        if "reminder_minutes" in event_data:
            event.reminder_minutes = event_data["reminder_minutes"]

        await self.db.commit()
        await self.db.refresh(event)

        return event
    
    async def delete_event(
        self,
        event_id: str,
        user_id: str,
    ) -> bool:
        """Delete an event."""
        result = await self.db.execute(
            select(Event).where(
                Event.id == event_id,
                Event.tenant_id == self.tenant_id,
            )
        )
        event = result.scalar_one_or_none()
        
        if not event:
            return False
        
        await self.db.delete(event)
        await self.db.commit()
        return True
    
    async def sync_event_to_external(
        self,
        event_id: str,
        provider: str,
        user_id: str,
    ) -> Dict[str, Any]:
        """Sync an event to external calendar (Microsoft/Google)."""
        event = await self.get_event(event_id, user_id)
        
        if not event:
            raise ValueError("Event not found")
        
        if provider == "microsoft":
            from app.integrations.microsoft import MicrosoftCalendar
            ms_calendar = MicrosoftCalendar(self.db, self.tenant_id)
            result = await ms_calendar.create_event(event)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Update event with external ID
        event.external_event_id = result.get("id")
        event.sync_provider = provider
        await self.db.flush()
        
        return result
    
    async def _schedule_reminders(self, event: Event):
        """Schedule reminders for an event."""
        if not event.reminder_minutes:
            return
        
        # This would create Celery tasks for reminders
        # For now, we just mark the event as needing reminders
        pass
