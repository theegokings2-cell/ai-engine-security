"""Models package - Import all models to register with SQLAlchemy."""

# Import all models so SQLAlchemy can resolve relationships
from app.models.user import User
from app.models.tenant import Tenant
from app.models.task import Task
from app.models.note import Note
from app.models.audit_log import AuditLog
from app.models.event import Event
from app.models.role import Role

# Office models
from app.models.office.office_models import (
    Department, Employee, Location, MeetingRoom, Resource,
    RoomBooking, ResourceBooking, Customer, CustomerContact,
    Appointment, TimeEntry, Attendance,
)

# Portal models
from app.models.portal import CustomerUser, CustomerSession

# Automation models
from app.models.automation import (
    WorkflowTemplate, WorkflowExecution, AgentTask, AutomationRule
)

__all__ = [
    "User", "Tenant", "Task", "Note", "AuditLog", "Event", "Role",
    "Department", "Employee", "Location", "MeetingRoom", "Resource",
    "RoomBooking", "ResourceBooking", "Customer", "CustomerContact",
    "Appointment", "TimeEntry", "Attendance",
    "CustomerUser", "CustomerSession",
    "WorkflowTemplate", "WorkflowExecution", "AgentTask", "AutomationRule",
]
