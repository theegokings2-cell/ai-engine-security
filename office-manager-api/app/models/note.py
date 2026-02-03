"""
Note model with AI summarization support.
"""
from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID as PyUUID, uuid4

from pydantic import BaseModel, field_serializer
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import TenantMixin, TimestampMixin


class Note(Base, TenantMixin, TimestampMixin):
    """Meeting note model with AI features."""
    
    __tablename__ = "notes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    meeting_context = Column(Text, nullable=True)  # Who, what, when
    
    # AI-generated summary
    ai_summary = Column(Text, nullable=True)
    ai_action_items = Column(Text, nullable=True)  # JSON array
    ai_key_topics = Column(Text, nullable=True)  # JSON array
    ai_sentiment = Column(Text, nullable=True)
    
    # Source info
    source_type = Column(Text, default="manual")  # manual, meeting_transcript, email
    source_id = Column(Text, nullable=True)
    
    # RAG document reference
    is_rag_document = Column(Text, default="N")
    document_type = Column(Text, nullable=True)  # policy, handbook, procedure
    
    # Creator
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Relationships
    created_by = relationship("User", back_populates="created_notes")
    
    def __repr__(self) -> str:
        return f"<Note(id={self.id}, title={self.title[:50]}...)>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "title": self.title,
            "content": self.content,
            "meeting_context": self.meeting_context,
            "ai_summary": self.ai_summary,
            "ai_action_items": self.ai_action_items,
            "ai_key_topics": self.ai_key_topics,
            "ai_sentiment": self.ai_sentiment,
            "source_type": self.source_type,
            "is_rag_document": self.is_rag_document == "Y",
            "created_by_id": str(self.created_by_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Pydantic schemas
class NoteCreate(BaseModel):
    """Schema for note creation."""
    title: str
    content: str
    meeting_context: Optional[str] = None


class NoteUpdate(BaseModel):
    """Schema for note update."""
    title: Optional[str] = None
    content: Optional[str] = None
    meeting_context: Optional[str] = None


class NoteResponse(BaseModel):
    """Schema for note response."""
    id: Union[str, PyUUID]
    tenant_id: Union[str, PyUUID]
    title: str
    content: str
    meeting_context: Optional[str]
    ai_summary: Optional[str]
    ai_action_items: Optional[str]
    ai_key_topics: Optional[str]
    ai_sentiment: Optional[str]
    source_type: Optional[str]
    created_by_id: Union[str, PyUUID]
    created_at: datetime

    class Config:
        from_attributes = True

    @field_serializer('id', 'tenant_id', 'created_by_id')
    def serialize_uuid(self, value: Any) -> str:
        return str(value) if value else None


class SummarizeResponse(BaseModel):
    """Response for note summarization."""
    id: str
    summary: str
    action_items: list[dict]
    key_topics: list[str]
    sentiment: str


class QAResponse(BaseModel):
    """Response for Q&A on notes."""
    answer: str
    sources: list[dict]
