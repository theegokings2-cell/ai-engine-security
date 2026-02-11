-- AI Agent Automation Tables
-- Workflows, automation rules, and AI agent actions

-- ============================================
-- WORKFLOW TEMPLATES
-- ============================================
CREATE TABLE IF NOT EXISTS workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_type VARCHAR(50) NOT NULL, -- 'scheduled', 'event', 'webhook', 'manual'
    trigger_config JSONB, -- Schedule (cron), event filters, or webhook config
    conditions JSONB, -- Conditions that must be met
    actions JSONB NOT NULL, -- Array of actions to execute
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- Higher priority runs first
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, name)
);

-- Index for workflow lookups
CREATE INDEX IF NOT EXISTS idx_workflow_templates_tenant ON workflow_templates(tenant_id);
CREATE INDEX IF NOT EXISTS idx_workflow_templates_active ON workflow_templates(is_active) WHERE is_active = TRUE;

-- ============================================
-- WORKFLOW EXECUTION LOG
-- ============================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workflow_template_id UUID REFERENCES workflow_templates(id),
    trigger_type VARCHAR(50) NOT NULL,
    trigger_context JSONB, -- What triggered this execution
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    output JSONB, -- Results of each action
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workflow_executions_tenant ON workflow_executions(tenant_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_workflow ON workflow_executions(workflow_template_id);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_created ON workflow_executions(created_at DESC);

-- ============================================
-- AI AGENT TASKS
-- ============================================
CREATE TABLE IF NOT EXISTS agent_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL, -- 'summarize', 'follow_up', 'reminder', 'response', 'analysis'
    priority VARCHAR(20) DEFAULT 'normal', -- urgent, normal, low
    input_data JSONB NOT NULL, -- Input for the AI task
    instructions TEXT, -- Specific instructions for the AI
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    result JSONB, -- AI output
    assigned_to_user_id UUID REFERENCES users(id), -- Who requested/owns this
    created_by UUID REFERENCES users(id),
    scheduled_at TIMESTAMP, -- When to run (for scheduled tasks)
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_agent_tasks_tenant ON agent_tasks(tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_scheduled ON agent_tasks(scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_agent_tasks_type ON agent_tasks(task_type);

-- ============================================
-- AUTOMATION RULES
-- ============================================
CREATE TABLE IF NOT EXISTS automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    event_type VARCHAR(100) NOT NULL, -- 'appointment.created', 'customer.created', 'task.completed', etc.
    conditions JSONB, -- Conditions that must be true
    actions JSONB NOT NULL, -- Actions to take
    is_active BOOLEAN DEFAULT TRUE,
    cooldown_minutes INTEGER DEFAULT 0, -- Minimum time between executions
    last_triggered TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, name)
);

-- Index
CREATE INDEX IF NOT EXISTS idx_automation_rules_tenant ON automation_rules(tenant_id);
CREATE INDEX IF NOT EXISTS idx_automation_rules_event ON automation_rules(event_type);

-- ============================================
-- COMMON AUTOMATION TEMPLATES
-- ============================================

-- Appointment Reminder Workflow
INSERT INTO workflow_templates (tenant_id, name, description, trigger_type, trigger_config, actions, is_active, priority) VALUES
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'Appointment Reminders', 'Send automatic reminders 24h and 1h before appointments', 'scheduled', 
     '{"schedule": "0 * * * *", "description": "Run every hour"}', -- Check every hour
     '[
       {"type": "find_appointments", "params": {"reminder_window": "24 hours", "status": "scheduled"}},
       {"type": "send_reminder", "params": {"channel": "telegram", "timing": "24h"}},
       {"type": "send_reminder", "params": {"channel": "telegram", "timing": "1h"}}
     ]',
     FALSE, 10);

-- Customer Follow-up Workflow
INSERT INTO workflow_templates (tenant_id, name, description, trigger_type, trigger_config, actions, is_active, priority) VALUES
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'Appointment Follow-up', 'Send follow-up message 1h after completed appointments', 'event',
     '{"event": "appointment.completed", "description": "When appointment is marked completed"}',
     '[
       {"type": "create_agent_task", "params": {"task_type": "follow_up", "instructions": "Generate personalized follow-up message based on appointment notes"}}
     ]',
     FALSE, 5);

-- Daily Task Summary Workflow
INSERT INTO workflow_templates (tenant_id, name, description, trigger_type, trigger_config, actions, is_active, priority) VALUES
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'Daily Task Summary', 'Send daily task summary each morning at 8am', 'scheduled',
     '{"schedule": "0 8 * * *", "description": "Daily at 8 AM"}',
     '[
       {"type": "aggregate_tasks", "params": {"status": "todo", "assigned_to": "all"}},
       {"type": "generate_summary", "params": {"task_type": "task_summary"}},
       {"type": "send_digest", "params": {"channel": "telegram"}}
     ]',
     FALSE, 20);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Get active workflows for tenant
CREATE OR REPLACE FUNCTION get_active_workflows(tenant_id_input uuid)
RETURNS TABLE (id uuid, name varchar, trigger_type varchar, priority int) AS $$
BEGIN
    RETURN QUERY 
    SELECT wt.id, wt.name, wt.trigger_type, wt.priority
    FROM workflow_templates wt
    WHERE wt.tenant_id = tenant_id_input AND wt.is_active = TRUE
    ORDER BY wt.priority DESC;
END;
$$ LANGUAGE plpgsql;

-- Log workflow execution
CREATE OR REPLACE FUNCTION log_workflow_execution(
    p_tenant_id uuid,
    p_workflow_id uuid,
    p_trigger_type varchar,
    p_trigger_context jsonb
)
RETURNS uuid AS $$
DECLARE
    v_execution_id uuid;
BEGIN
    INSERT INTO workflow_executions (
        tenant_id, workflow_template_id, trigger_type, trigger_context, status
    ) VALUES (
        p_tenant_id, p_workflow_id, p_trigger_type, p_trigger_context, 'running'
    )
    RETURNING id INTO v_execution_id;
    
    RETURN v_execution_id;
END;
$$ LANGUAGE plpgsql;

-- Complete workflow execution
CREATE OR REPLACE FUNCTION complete_workflow_execution(
    p_execution_id uuid,
    p_status varchar,
    p_output jsonb DEFAULT NULL,
    p_error_message text DEFAULT NULL
)
RETURNS void AS $$
BEGIN
    UPDATE workflow_executions SET
        status = p_status,
        completed_at = NOW(),
        output = p_output,
        error_message = p_error_message
    WHERE id = p_execution_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFY
-- ============================================
SELECT 'workflow_templates' as table_name, COUNT(*) as count FROM workflow_templates
UNION ALL SELECT 'workflow_executions', COUNT(*) FROM workflow_executions
UNION ALL SELECT 'agent_tasks', COUNT(*) FROM agent_tasks
UNION ALL SELECT 'automation_rules', COUNT(*) FROM automation_rules;
