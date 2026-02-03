"""
Task model for task management.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID as PyUUID, uuid4

from pydantic import BaseModel, field_serializer
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import TenantMixin, TimestampMixin


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority values."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Task(Base, TenantMixin, TimestampMixin):
    """Task model."""
    
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=TaskStatus.PENDING.value, nullable=False)
    priority = Column(String(20), default=TaskPriority.MEDIUM.value, nullable=False)
    
    # Assignment
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Dates
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Reminder
    reminder_enabled = Column(String(1), default="Y")
    reminder_sent = Column(String(1), default="N")
    reminder_channel = Column(String(20), default="email")  # email, sms, telegram
    reminder_at = Column(DateTime(timezone=True), nullable=True)
    
    # AI-generated fields
    ai_priority_score: Optional[float] = Column(Text, nullable=True)
    
    # Natural language source
    nl_source_text: Optional[Text] = Column(Text, nullable=True)  # Original text for NL parsing
    
    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[creator_id])
    assignee = relationship("User", back_populates="tasks", foreign_keys=[assignee_id])
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "assignee_id": str(self.assignee_id) if self.assignee_id else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "reminder_enabled": self.reminder_enabled == "Y",
            "reminder_sent": self.reminder_sent == "Y",
            "reminder_channel": self.reminder_channel,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Pydantic schemas
class TaskCreate(BaseModel):
    """Schema for task creation."""
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None
    reminder_enabled: bool = True
    reminder_channel: str = "email"


class TaskUpdate(BaseModel):
    """Schema for task update."""
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee_id: Optional[str] = None
    due_date: Optional[datetime] = None


class TaskFromText(BaseModel):
    """Schema for natural language task creation."""
    text: str


class TaskResponse(BaseModel):
    """Schema for task response."""
    id: Union[str, PyUUID]
    tenant_id: Union[str, PyUUID]
    title: str
    description: Optional[str]
    status: str
    priority: str
    assignee_id: Optional[Union[str, PyUUID]]
    assignee_name: Optional[str] = None
    due_date: Optional[datetime]
    reminder_enabled: Any  # Can be "Y"/"N" or bool
    reminder_channel: str
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('id', 'tenant_id')
    def serialize_uuid(self, value: Any) -> str:
        return str(value) if value else None

    @field_serializer('assignee_id')
    def serialize_assignee_id(self, value: Any) -> Optional[str]:
        return str(value) if value else None

    @field_serializer('reminder_enabled')
    def serialize_reminder_enabled(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return value == "Y" if value else False
