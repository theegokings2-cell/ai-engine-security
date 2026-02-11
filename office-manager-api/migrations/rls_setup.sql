-- Row-Level Security (RLS) Migration for Office Manager API
-- PostgreSQL RLS provides database-level tenant isolation
-- Run this after creating all tables: psql -d office_manager -f migrations/rls_setup.sql

-- Enable RLS on all tenant-scoped tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for each table
-- These policies restrict access based on the 'app.current_tenant_id' session variable

-- Users table policy
CREATE POLICY "Users can only access their tenant's users" ON users
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Tasks table policy
CREATE POLICY "Tasks can only access their tenant's tasks" ON tasks
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Notes table policy
CREATE POLICY "Notes can only access their tenant's notes" ON notes
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Events table policy
CREATE POLICY "Events can only access their tenant's events" ON events
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Audit logs table policy (admin can see all within tenant)
CREATE POLICY "Audit logs tenant isolation" ON audit_logs
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Create a function to safely set tenant context
-- This will be called by the application before each query
CREATE OR REPLACE FUNCTION set_tenant_context(tenant_id_input uuid)
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', tenant_id_input::text, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to clear tenant context (for logout/cleanup)
CREATE OR REPLACE FUNCTION clear_tenant_context()
RETURNS void AS $$
BEGIN
    PERFORM set_config('app.current_tenant_id', '', true);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute on functions to authenticated users
-- (adjust based on your DB user setup)

-- Verify RLS is enabled
SELECT 
    tablename,
    rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('users', 'tasks', 'notes', 'events', 'audit_logs');

-- List all RLS policies
SELECT 
    policyname,
    tablename,
    cmd,
    qual
FROM pg_policies
WHERE schemaname = 'public';

-- Testing RLS (run as postgres superuser to bypass policies)
-- 1. Set tenant context
-- SELECT set_tenant_context('your-tenant-uuid-here');
-- 2. Test access - should only return rows for that tenant
-- SELECT * FROM users;
-- 3. Clear context
-- SELECT clear_tenant_context();

-- Rollback script (if needed)
-- DROP POLICY IF EXISTS "Users can only access their tenant's users" ON users;
-- DROP POLICY IF EXISTS "Tasks can only access their tenant's tasks" ON tasks;
-- DROP POLICY IF EXISTS "Notes can only access their tenant's notes" ON notes;
-- DROP POLICY IF EXISTS "Events can only access their tenant's events" ON events;
-- DROP POLICY IF EXISTS "Audit logs tenant isolation" ON audit_logs;
-- ALTER TABLE users DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE tasks DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE notes DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE events DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_logs DISABLE ROW LEVEL SECURITY;
-- DROP FUNCTION IF EXISTS set_tenant_context(uuid);
-- DROP FUNCTION IF EXISTS clear_tenant_context();
