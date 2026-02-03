"""
Calendar event model.
"""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Union
from uuid import UUID as PyUUID, uuid4

from pydantic import BaseModel, field_validator, field_serializer
from sqlalchemy import Column, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import TenantMixin, TimestampMixin


class EventType(str, Enum):
    """Event type values."""
    MEETING = "meeting"
    CALL = "call"
    REMINDER = "reminder"
    BLOCKED = "blocked"


class Event(Base, TenantMixin, TimestampMixin):
    """Calendar event model."""
    
    __tablename__ = "events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(20), default=EventType.MEETING.value, nullable=False)
    
    # Timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    all_day = Column(String(1), default="N")
    timezone = Column(String(50), default="UTC")
    
    # Location
    location: Optional[str] = Column(String(255), nullable=True)
    meeting_link: Optional[str] = Column(String(500), nullable=True)
    
    # Attendees
    attendees = Column(ARRAY(String(255)), default=[])  # Email addresses
    
    # External sync
    external_calendar_id: Optional[str] = Column(String(255), nullable=True)
    external_event_id: Optional[str] = Column(String(255), nullable=True)
    sync_provider: Optional[str] = Column(String(50), nullable=True)  # microsoft, google
    
    # Recurrence
    is_recurring = Column(String(1), default="N")
    recurrence_rule: Optional[str] = Column(String(255), nullable=True)  # RRULE format
    
    # Reminder
    reminder_minutes: Optional[int] = Column(JSONB, nullable=True)  # [15, 60, 1440]
    
    # Creator
    created_by_id = Column(UUID(as_uuid=True), nullable=False)
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, title={self.title}, start={self.start_time})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "all_day": self.all_day == "Y",
            "location": self.location,
            "meeting_link": self.meeting_link,
            "attendees": self.attendees,
            "reminder_minutes": self.reminder_minutes,
            "created_by_id": str(self.created_by_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Pydantic schemas
class EventCreate(BaseModel):
    """Schema for event creation."""
    title: str
    description: Optional[str] = None
    event_type: EventType = EventType.MEETING
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    timezone: str = "UTC"
    location: Optional[str] = None
    attendees: List[str] = []
    reminder_minutes: Optional[List[int]] = [15, 60]


class EventUpdate(BaseModel):
    """Schema for event update."""
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[EventType] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    reminder_minutes: Optional[List[int]] = None


class EventResponse(BaseModel):
    """Schema for event response."""
    id: Union[str, PyUUID]
    tenant_id: Union[str, PyUUID]
    title: str
    description: Optional[str]
    event_type: str
    start_time: datetime
    end_time: datetime
    all_day: Any  # Can be "Y"/"N" or bool
    location: Optional[str]
    meeting_link: Optional[str]
    attendees: Optional[List[str]]
    reminder_minutes: Optional[List[int]]
    created_by_id: Union[str, PyUUID]
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('id', 'tenant_id', 'created_by_id')
    def serialize_uuid(self, value: Any) -> str:
        return str(value) if value else None

    @field_serializer('all_day')
    def serialize_all_day(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return value == "Y" if value else False

    @field_serializer('attendees')
    def serialize_attendees(self, value: Any) -> List[str]:
        return value or []
