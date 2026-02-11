-- Employee Portal Permission System Migration
-- Adds permissions table, user permission columns, and SCIM group mapping

-- ============================================
-- USER PERMISSIONS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS user_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(100) NOT NULL,
    granted_at TIMESTAMP DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(user_id, permission)
);

-- Index for fast permission lookups
CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_tenant ON user_permissions(tenant_id);

-- ============================================
-- SCIM GROUP MAPPING TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS scim_group_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    idp_name VARCHAR(50) NOT NULL, -- 'okta', 'entra', 'google'
    idp_group_name VARCHAR(255) NOT NULL,
    system_role VARCHAR(50) NOT NULL DEFAULT 'employee',
    department_id UUID REFERENCES departments(id),
    auto_assign BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- Higher priority wins if multiple groups match
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(tenant_id, idp_name, idp_group_name)
);

-- Index for group lookups
CREATE INDEX IF NOT EXISTS idx_scim_group_mappings_tenant ON scim_group_mappings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_scim_group_mappings_idp ON scim_group_mappings(idp_name, idp_group_name);

-- ============================================
-- AUDIT LOGS TABLE (Enhanced)
-- ============================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    correlation_id UUID, -- For tracing requests end-to-end
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    request_path TEXT,
    request_method VARCHAR(10),
    risk_level VARCHAR(20) DEFAULT 'low', -- low, medium, high, critical
    blocked BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_correlation ON audit_logs(correlation_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_risk ON audit_logs(risk_level) WHERE risk_level IN ('high', 'critical');

-- ============================================
-- EXTEND RLS POLICIES FOR EMPLOYEE ACCESS
-- ============================================

-- Appointments: Only see own OR assigned appointments
DROP POLICY IF EXISTS appointments_tenant_isolation ON appointments;
CREATE POLICY appointments_tenant_isolation ON appointments
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::uuid AND
        (
            assigned_to_id = current_setting('app.current_user_id', true)::uuid OR
            owner_id = current_setting('app.current_user_id', true)::uuid
        )
    );

-- Tasks: Only see assigned tasks
DROP POLICY IF EXISTS tasks_tenant_isolation ON tasks;
CREATE POLICY tasks_tenant_isolation ON tasks
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::uuid AND
        assigned_to_id = current_setting('app.current_user_id', true)::uuid
    );

-- Notes: See own notes OR notes shared with department
DROP POLICY IF EXISTS notes_tenant_isolation ON notes;
CREATE POLICY notes_tenant_isolation ON notes
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::uuid AND
        (
            created_by_id = current_setting('app.current_user_id', true)::uuid OR
            shared_with_department = current_setting('app.current_department_id', true)::uuid
        )
    );

-- Customers: See assigned customers OR department-scoped
DROP POLICY IF EXISTS customers_tenant_isolation ON customers;
CREATE POLICY customers_tenant_isolation ON customers
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::uuid AND
        (
            assigned_employee_id = current_setting('app.current_user_id', true)::uuid OR
            department_id = current_setting('app.current_department_id', true)::uuid
        )
    );

-- Time Entries: Only see own entries
DROP POLICY IF EXISTS time_entries_tenant_isolation ON time_entries;
CREATE POLICY time_entries_tenant_isolation ON time_entries
    FOR ALL
    USING (
        tenant_id = current_setting('app.current_tenant_id', true)::uuid AND
        employee_id = current_setting('app.current_user_id', true)::uuid
    );

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Function to check if user has a specific permission
CREATE OR REPLACE FUNCTION has_permission(user_id_input uuid, permission_required VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_permissions
        WHERE user_id = user_id_input
          AND permission = permission_required
          AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to get user permissions as JSON
CREATE OR REPLACE FUNCTION get_user_permissions(user_id_input uuid)
RETURNS JSONB AS $$
BEGIN
    RETURN (
        SELECT jsonb_agg(permission)
        FROM user_permissions
        WHERE user_id = user_id_input
          AND (expires_at IS NULL OR expires_at > NOW())
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to log audit event
CREATE OR REPLACE FUNCTION log_audit_event(
    p_tenant_id uuid,
    p_user_id uuid,
    p_action VARCHAR,
    p_resource_type VARCHAR,
    p_resource_id VARCHAR DEFAULT NULL,
    p_old_values JSONB DEFAULT NULL,
    p_new_values JSONB DEFAULT NULL,
    p_ip INET DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_risk_level VARCHAR DEFAULT 'low',
    p_blocked BOOLEAN DEFAULT FALSE,
    p_error_message TEXT DEFAULT NULL
)
RETURNS uuid AS $$
DECLARE
    v_correlation_id uuid;
    v_audit_id uuid;
BEGIN
    v_correlation_id := gen_random_uuid();
    
    INSERT INTO audit_logs (
        tenant_id,
        user_id,
        correlation_id,
        action,
        resource_type,
        resource_id,
        old_values,
        new_values,
        ip_address,
        user_agent,
        risk_level,
        blocked,
        error_message
    ) VALUES (
        p_tenant_id,
        p_user_id,
        v_correlation_id,
        p_action,
        p_resource_type,
        p_resource_id,
        p_old_values,
        p_new_values,
        p_ip,
        p_user_agent,
        p_risk_level,
        p_blocked,
        p_error_message
    )
    RETURNING id INTO v_audit_id;
    
    RETURN v_audit_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================
-- DEFAULT SCIM GROUP MAPPINGS
-- ============================================
INSERT INTO scim_group_mappings (tenant_id, idp_name, idp_group_name, system_role, priority) VALUES
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'okta', 'Admins', 'admin', 100),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'okta', 'Managers', 'manager', 90),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'okta', 'Employees', 'employee', 50),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'okta', 'Sales-Team', 'employee', 50),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'okta', 'Support-Team', 'employee', 50),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'entra', 'Admins', 'admin', 100),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'entra', 'Managers', 'manager', 90),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'entra', 'Employees', 'employee', 50),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'google', 'Admins', 'admin', 100),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'google', 'Managers', 'manager', 90),
    ('5061ddb5-6ee0-4001-b931-2ebaed4e3474', 'google', 'Employees', 'employee', 50)
ON CONFLICT DO NOTHING;

-- ============================================
-- VERIFY
-- ============================================
SELECT 'user_permissions' as table_name, COUNT(*) as count FROM user_permissions
UNION ALL
SELECT 'scim_group_mappings', COUNT(*) FROM scim_group_mappings
UNION ALL
SELECT 'audit_logs', COUNT(*) FROM audit_logs;

-- List all RLS policies
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE schemaname = 'public'
    AND tablename IN ('appointments', 'tasks', 'notes', 'customers', 'time_entries')
ORDER BY tablename;
