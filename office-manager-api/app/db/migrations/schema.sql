-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tenants table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    settings JSONB DEFAULT '{}',
    subscription_tier VARCHAR(20) DEFAULT 'free',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'employee',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    phone VARCHAR(20),
    telegram_chat_id VARCHAR(50),
    notification_preference VARCHAR(20) DEFAULT 'email',
    password_reset_token VARCHAR(255),
    password_reset_expires TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    permissions TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    reminder_enabled CHAR(1) DEFAULT 'Y',
    reminder_sent CHAR(1) DEFAULT 'N',
    reminder_channel VARCHAR(20) DEFAULT 'email',
    reminder_at TIMESTAMPTZ,
    ai_priority_score TEXT,
    nl_source_text TEXT,
    deleted_at TIMESTAMPTZ,
    is_deleted CHAR(1) DEFAULT 'N',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tasks_tenant ON tasks(tenant_id);
CREATE INDEX idx_tasks_assignee ON tasks(assignee_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due ON tasks(due_date);

-- Events table
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(20) DEFAULT 'meeting',
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    all_day CHAR(1) DEFAULT 'N',
    timezone VARCHAR(50) DEFAULT 'UTC',
    location VARCHAR(255),
    meeting_link VARCHAR(500),
    attendees TEXT[],
    external_calendar_id VARCHAR(255),
    external_event_id VARCHAR(255),
    sync_provider VARCHAR(50),
    is_recurring CHAR(1) DEFAULT 'N',
    recurrence_rule VARCHAR(255),
    reminder_minutes JSONB,
    created_by_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_tenant ON events(tenant_id);
CREATE INDEX idx_events_start ON events(start_time);
CREATE INDEX idx_events_created_by ON events(created_by_id);

-- Notes table
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    meeting_context TEXT,
    ai_summary TEXT,
    ai_action_items TEXT,
    ai_key_topics TEXT,
    ai_sentiment TEXT,
    source_type VARCHAR(50) DEFAULT 'manual',
    source_id VARCHAR(255),
    is_rag_document CHAR(1) DEFAULT 'N',
    document_type VARCHAR(50),
    created_by_id UUID NOT NULL,
    deleted_at TIMESTAMPTZ,
    is_deleted CHAR(1) DEFAULT 'N',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notes_tenant ON notes(tenant_id);
CREATE INDEX idx_notes_created_by ON notes(created_by_id);

-- Audit logs table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id UUID,
    old_values TEXT,
    new_values TEXT,
    metadata TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_tenant ON audit_logs(tenant_id);
CREATE INDEX idx_audit_user ON audit_logs(user_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at);

-- Insert default roles
INSERT INTO roles (name, description, permissions) VALUES
('admin', 'Full access to all features', '[
    "user:create", "user:read", "user:update", "user:delete",
    "task:create", "task:read", "task:update", "task:delete", "task:assign",
    "event:create", "event:read", "event:update", "event:delete",
    "note:create", "note:read", "note:update", "note:delete", "note:summarize", "note:qa",
    "admin:audit", "admin:settings"
]'),
('manager', 'Team management access', '[
    "user:read",
    "task:create", "task:read", "task:update", "task:assign",
    "event:create", "event:read", "event:update",
    "note:create", "note:read", "note:update", "note:summarize", "note:qa"
]'),
('employee', 'Basic user access', '[
    "task:create", "task:read", "task:update",
    "event:read",
    "note:create", "note:read", "note:update", "note:summarize", "note:qa"
]');
