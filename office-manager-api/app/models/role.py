"""
Role and Permission models for RBAC.
"""
from datetime import datetime
from enum import Enum
from typing import List
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Permission(str, Enum):
    """Available permissions in the system."""
    
    # User Management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Task Management
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    TASK_DELETE = "task:delete"
    TASK_ASSIGN = "task:assign"
    
    # Calendar
    EVENT_CREATE = "event:create"
    EVENT_READ = "event:read"
    EVENT_UPDATE = "event:update"
    EVENT_DELETE = "event:delete"
    
    # Notes
    NOTE_CREATE = "note:create"
    NOTE_READ = "note:read"
    NOTE_UPDATE = "note:update"
    NOTE_DELETE = "note:delete"
    NOTE_SUMMARIZE = "note:summarize"
    NOTE_QA = "note:qa"
    
    # Admin
    ADMIN_AUDIT = "admin:audit"
    ADMIN_SETTINGS = "admin:settings"
    ADMIN_USERS = "admin:users"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[str, List[Permission]] = {
    "admin": list(Permission),  # All permissions
    "manager": [
        Permission.USER_READ,
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,
        Permission.TASK_ASSIGN,
        Permission.EVENT_CREATE,
        Permission.EVENT_READ,
        Permission.EVENT_UPDATE,
        Permission.NOTE_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_UPDATE,
        Permission.NOTE_SUMMARIZE,
        Permission.NOTE_QA,
    ],
    "employee": [
        Permission.TASK_CREATE,
        Permission.TASK_READ,
        Permission.TASK_UPDATE,  # Only own tasks enforced in service
        Permission.EVENT_READ,
        Permission.NOTE_CREATE,
        Permission.NOTE_READ,
        Permission.NOTE_UPDATE,  # Only own notes enforced in service
        Permission.NOTE_SUMMARIZE,
        Permission.NOTE_QA,
    ],
}


class Role(Base):
    """Role model for RBAC."""
    
    __tablename__ = "roles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(50), unique=True, nullable=False)  # admin, manager, employee
    description = Column(String(255), nullable=True)
    permissions = Column(String, nullable=False)  # JSON array of permission strings
    
    def __repr__(self) -> str:
        return f"<Role(name={self.name})>"
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if role has specific permission."""
        from app.models.role import ROLE_PERMISSIONS
        role_perms = ROLE_PERMISSIONS.get(self.name, [])
        return permission in role_perms
    
    @classmethod
    def get_default_roles(cls) -> List[dict]:
        """Get default role definitions."""
        import json
        return [
            {
                "name": "admin",
                "description": "Full access to all features",
                "permissions": json.dumps([p.value for p in Permission]),
            },
            {
                "name": "manager",
                "description": "Team management access",
                "permissions": json.dumps([p.value for p in ROLE_PERMISSIONS["manager"]]),
            },
            {
                "name": "employee",
                "description": "Basic user access",
                "permissions": json.dumps([p.value for p in ROLE_PERMISSIONS["employee"]]),
            },
        ]
