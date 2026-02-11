"""
Base SQLAlchemy model with common fields.
"""
import uuid
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr, Mapped, mapped_column

from app.db.session import Base


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""
    
    @declared_attr
    def created_at(cls) -> Mapped[datetime]:
        return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @declared_attr
    def updated_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantMixin:
    """Mixin for tenant-scoped models."""
    
    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), nullable=False, index=True)


class SoftDeleteMixin:
    """Mixin for soft-delete functionality."""
    
    @declared_attr
    def deleted_at(cls) -> Mapped[Optional[datetime]]:
        return mapped_column(DateTime(timezone=True), nullable=True)
    
    @declared_attr
    def is_deleted(cls) -> Mapped[str]:
        return mapped_column(String(1), default="N", nullable=False)


ModelType = TypeVar("ModelType", bound=Base)


class BaseModel(Base):
    """Base model with common fields."""
    
    __abstract__ = True
    __allow_unmapped__ = True
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        return {
            c.name: getattr(self, c.name)
            for c in self.__table__.columns
            if c.name not in ("created_at", "updated_at")
        }
