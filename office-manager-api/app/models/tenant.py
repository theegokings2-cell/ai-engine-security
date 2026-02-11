"""
Tenant model with settings.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import TenantMixin, TimestampMixin


class SubscriptionTier(str, Enum):
    """Tenant subscription tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantSettings(BaseModel):
    """Tenant configuration settings."""
    email_provider: str = "microsoft"  # microsoft, google
    sms_enabled: bool = True
    telegram_enabled: bool = True
    calendar_provider: str = "microsoft"  # microsoft, google
    ai_summarization_enabled: bool = True
    ai_rag_enabled: bool = False
    max_users: int = 10
    max_storage_gb: int = 5
    reminder_hours_before: int = 24


class Tenant(Base, TimestampMixin):
    """Tenant (organization) model."""
    
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    settings = Column(JSONB, default={})
    subscription_tier = Column(String(20), default=SubscriptionTier.FREE.value)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    users = relationship("User", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, slug={self.slug})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "settings": self.settings,
            "subscription_tier": self.subscription_tier,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
