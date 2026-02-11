"""
User model with role-based access control.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import uuid4, UUID as PyUUID

from pydantic import BaseModel, EmailStr, field_serializer
from sqlalchemy import Boolean, Column, DateTime, String, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin


class UserRole(str, Enum):
    """User roles."""
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"
    CUSTOMER = "customer"


class UserPermissions:
    """Permission definitions for the system."""
    # Calendar permissions
    CALENDAR_READ = "calendar.read"
    CALENDAR_WRITE = "calendar.write"
    
    # Appointment permissions
    APPOINTMENTS_READ_OWN = "appointments.read_own"
    APPOINTMENTS_READ_ALL = "appointments.read_all"
    APPOINTMENTS_WRITE_OWN = "appointments.write_own"
    
    # Task permissions
    TASKS_READ_OWN = "tasks.read_own"
    TASKS_READ_ALL = "tasks.read_all"
    TASKS_WRITE_ASSIGNED = "tasks.write_assigned"
    
    # Note permissions
    NOTES_WRITE_OWN = "notes.write_own"
    NOTES_READ_TEAM = "notes.read_team"
    
    # Customer permissions
    CUSTOMERS_READ_ASSIGNED = "customers.read_assigned"
    CUSTOMERS_READ_ALL = "customers.read_all"
    
    # Time tracking
    TIME_CREATE = "time.create"
    
    # Admin permissions
    ADMIN_FULL = "admin.full"
    
    @classmethod
    def get_role_default_permissions(cls, role: str) -> list:
        """Get default permissions based on role."""
        role_permissions = {
            UserRole.ADMIN.value: [
                cls.CALENDAR_READ, cls.CALENDAR_WRITE,
                cls.APPOINTMENTS_READ_ALL, cls.APPOINTMENTS_WRITE_OWN,
                cls.TASKS_READ_ALL, cls.TASKS_WRITE_ASSIGNED,
                cls.NOTES_WRITE_OWN, cls.NOTES_READ_TEAM,
                cls.CUSTOMERS_READ_ALL,
                cls.TIME_CREATE,
                cls.ADMIN_FULL,
            ],
            UserRole.MANAGER.value: [
                cls.CALENDAR_READ,
                cls.APPOINTMENTS_READ_ALL,
                cls.TASKS_READ_ALL, cls.TASKS_WRITE_ASSIGNED,
                cls.NOTES_WRITE_OWN, cls.NOTES_READ_TEAM,
                cls.CUSTOMERS_READ_ALL,
                cls.TIME_CREATE,
            ],
            UserRole.EMPLOYEE.value: [
                cls.CALENDAR_READ,
                cls.APPOINTMENTS_READ_OWN, cls.APPOINTMENTS_WRITE_OWN,
                cls.TASKS_READ_OWN, cls.TASKS_WRITE_ASSIGNED,
                cls.NOTES_WRITE_OWN,
                cls.CUSTOMERS_READ_ASSIGNED,
                cls.TIME_CREATE,
            ],
            UserRole.CUSTOMER.value: [
                cls.APPOINTMENTS_READ_OWN,
                cls.TASKS_READ_OWN,
                cls.NOTES_WRITE_OWN,
            ],
        }
        return role_permissions.get(role, [])


class NotificationPreference(str, Enum):
    """User notification preferences."""
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"


class User(Base, TimestampMixin):
    """User model with tenant scoping."""
    
    __tablename__ = "users"
    
    id: Mapped[uuid4] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[uuid4] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default=UserRole.EMPLOYEE.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Profile fields
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notification_preference: Mapped[str] = mapped_column(String(20), default=NotificationPreference.EMAIL.value)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")  # User's preferred timezone
    
    # Password reset
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships (commented out to avoid circular imports)
    # tenant = relationship("Tenant", back_populates="users")
    tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assignee_id")
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.creator_id")
    created_notes = relationship("Note", back_populates="created_by")
    audit_logs = relationship("AuditLog", back_populates="user")
    employee = relationship("Employee", back_populates="user", uselist=False)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        # Admin has all permissions
        if self.role == UserRole.ADMIN.value:
            return True
        
        # Check role-based default permissions
        default_perms = UserPermissions.get_role_default_permissions(self.role)
        if permission in default_perms:
            return True
        
        return False
    
    def get_all_permissions(self) -> list:
        """Get all permissions for this user."""
        return UserPermissions.get_role_default_permissions(self.role)
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary."""
        data = {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "phone": self.phone,
            "telegram_chat_id": self.telegram_chat_id,
            "notification_preference": self.notification_preference,
            "timezone": self.timezone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data["hashed_password"] = self.hashed_password
            data["password_reset_token"] = self.password_reset_token
            data["password_reset_expires"] = self.password_reset_expires.isoformat() if self.password_reset_expires else None
        
        return data


# Pydantic schemas for API requests/responses
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: str
    full_name: str
    password: str
    role: str = "employee"
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notification_preference: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user API responses."""
    id: Union[str, PyUUID]
    tenant_id: Union[str, PyUUID]
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    notification_preference: str
    timezone: str = "UTC"
    permissions: list = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_serializer('id', 'tenant_id')
    def serialize_uuid(self, value: Any) -> str:
        return str(value) if value else None
