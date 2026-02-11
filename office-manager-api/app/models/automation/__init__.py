"""
AI Agent Automation Models
Workflows, agent tasks, and automation rules.
"""
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base


class WorkflowTemplate(Base):
    """Workflow automation templates."""
    __tablename__ = "workflow_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(50), nullable=False)  # 'scheduled', 'event', 'webhook', 'manual'
    trigger_config = Column(JSONB, nullable=True)  # Schedule (cron), event filters, or webhook config
    conditions = Column(JSONB, nullable=True)  # Conditions that must be met
    actions = Column(JSONB, nullable=False)  # Array of actions to execute
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority runs first
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    executions = relationship("WorkflowExecution", back_populates="workflow")


class WorkflowExecution(Base):
    """Log of workflow executions."""
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    workflow_template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"))
    trigger_type = Column(String(50), nullable=False)
    trigger_context = Column(JSONB, nullable=True)  # What triggered this execution
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    output = Column(JSONB, nullable=True)  # Results of each action
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflow = relationship("WorkflowTemplate", back_populates="executions")


class AgentTask(Base):
    """AI agent tasks for background processing."""
    __tablename__ = "agent_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False)  # 'summarize', 'follow_up', 'reminder', 'response', 'analysis'
    priority = Column(String(20), default="normal")  # urgent, normal, low
    input_data = Column(JSONB, nullable=False)  # Input for the AI task
    instructions = Column(Text, nullable=True)  # Specific instructions for the AI
    status = Column(String(20), default="pending")  # pending, processing, completed, failed
    result = Column(JSONB, nullable=True)  # AI output
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutomationRule(Base):
    """Event-based automation rules."""
    __tablename__ = "automation_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    event_type = Column(String(100), nullable=False)  # 'appointment.created', 'customer.created', 'task.completed', etc.
    conditions = Column(JSONB, nullable=True)  # Conditions that must be true
    actions = Column(JSONB, nullable=False)  # Actions to take
    is_active = Column(Boolean, default=True)
    cooldown_minutes = Column(Integer, default=0)  # Minimum time between executions
    last_triggered = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
