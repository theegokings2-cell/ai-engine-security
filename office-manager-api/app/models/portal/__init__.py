"""
Customer Portal Models
User authentication and session management for customer portal
"""
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class CustomerUser(Base):
    """
    Customer portal user account
    
    Separate from internal users - customers access their data
    through this portal with limited permissions.
    """
    __tablename__ = "portal_customer_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    customer = relationship("Customer", backref="portal_users")
    sessions = relationship("CustomerSession", back_populates="customer_user")
    
    def __repr__(self) -> str:
        return f"<CustomerUser(id={self.id}, email={self.email})>"
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "customer_id": str(self.customer_id),
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "email_verified": self.email_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CustomerSession(Base):
    """
    Customer portal session tracking
    """
    __tablename__ = "portal_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_user_id = Column(UUID(as_uuid=True), ForeignKey("portal_customer_users.id"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    token = Column(Text, nullable=False, unique=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    customer_user = relationship("CustomerUser", back_populates="sessions")
    
    def __repr__(self) -> str:
        return f"<CustomerSession(id={self.id}, customer_user_id={self.customer_user_id})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": str(self.id),
            "customer_user_id": str(self.customer_user_id),
            "customer_id": str(self.customer_id),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
        }
