-- Comprehensive Row-Level Security (RLS) Migration for Office Manager API
-- Applies tenant isolation to ALL tables in the office management system
-- Run this AFTER the main RLS migration: psql -d office_manager -f migrations/comprehensive_rls.sql

-- ============================================
-- ENABLE RLS ON ALL TENANT-SCOPED TABLES
-- ============================================

-- Core tables (already in rls_setup.sql - verifying)
ALTER TABLE users ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE notes ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE events ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY IF NOT EXISTS;

-- Office Management tables
ALTER TABLE departments ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE employees ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE locations ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE meeting_rooms ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE room_bookings ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY IF NOT EXISTS;
ALTER TABLE attendances ENABLE ROW LEVEL SECURITY IF NOT EXISTS;

-- ============================================
-- CREATE RLS POLICIES FOR ALL TABLES
-- ============================================

-- Users table
CREATE POLICY IF NOT EXISTS "Users tenant isolation" ON users
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Tasks table
CREATE POLICY IF NOT EXISTS "Tasks tenant isolation" ON tasks
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Notes table
CREATE POLICY IF NOT EXISTS "Notes tenant isolation" ON notes
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Events table
CREATE POLICY IF NOT EXISTS "Events tenant isolation" ON events
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Audit logs table
CREATE POLICY IF NOT EXISTS "Audit logs tenant isolation" ON audit_logs
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Departments table
CREATE POLICY IF NOT EXISTS "Departments tenant isolation" ON departments
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Employees table
CREATE POLICY IF NOT EXISTS "Employees tenant isolation" ON employees
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Locations table
CREATE POLICY IF NOT EXISTS "Locations tenant isolation" ON locations
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Meeting rooms table
CREATE POLICY IF NOT EXISTS "Meeting rooms tenant isolation" ON meeting_rooms
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Room bookings table
CREATE POLICY IF NOT EXISTS "Room bookings tenant isolation" ON room_bookings
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Customers table
CREATE POLICY IF NOT EXISTS "Customers tenant isolation" ON customers
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Appointments table
CREATE POLICY IF NOT EXISTS "Appointments tenant isolation" ON appointments
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Time entries table
CREATE POLICY IF NOT EXISTS "Time entries tenant isolation" ON time_entries
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Attendance table
CREATE POLICY IF NOT EXISTS "Attendance tenant isolation" ON attendances
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- ============================================
-- BACKFILL MISSING TENANT_ID VALUES
-- ============================================
-- IMPORTANT: This section fixes records created before tenant isolation
-- Only run this ONCE when first enabling RLS

-- Create a helper function to backfill tenant_id
DO $$
DECLARE
    default_tenant_id uuid := '00000000-0000-0000-0000-000000000001'; -- Replace with actual tenant UUID
BEGIN
    -- Update departments with NULL tenant_id
    UPDATE departments SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update employees with NULL tenant_id
    UPDATE employees SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update locations with NULL tenant_id
    UPDATE locations SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update meeting_rooms with NULL tenant_id
    UPDATE meeting_rooms SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update room_bookings with NULL tenant_id
    UPDATE room_bookings SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update customers with NULL tenant_id
    UPDATE customers SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update appointments with NULL tenant_id
    UPDATE appointments SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update time_entries with NULL tenant_id
    UPDATE time_entries SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;

    -- Update attendances with NULL tenant_id
    UPDATE attendances SET tenant_id = default_tenant_id WHERE tenant_id IS NULL;
END $$;

-- ============================================
-- VERIFY RLS IS ENABLED
-- ============================================
SELECT
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
    AND tablename IN (
        'users', 'tasks', 'notes', 'events', 'audit_logs',
        'departments', 'employees', 'locations', 'meeting_rooms', 'room_bookings',
        'customers', 'appointments', 'time_entries', 'attendances'
    )
ORDER BY tablename;

-- List all RLS policies
SELECT
    policyname,
    tablename,
    cmd,
    CASE WHEN using_quals IS NOT NULL THEN 'USING: ' || using_quals ELSE '' END ||
    CASE WHEN check_quals IS NOT NULL THEN 'WITH CHECK: ' || check_quals ELSE '' END as policy_details
FROM pg_policies
WHERE schemaname = 'public'
    AND tablename IN (
        'users', 'tasks', 'notes', 'events', 'audit_logs',
        'departments', 'employees', 'locations', 'meeting_rooms', 'room_bookings',
        'customers', 'appointments', 'time_entries', 'attendances'
    )
ORDER BY tablename, policyname;

-- ============================================
-- ROLLBACK (if needed)
-- ============================================
-- DROP POLICY IF EXISTS "Users tenant isolation" ON users;
-- DROP POLICY IF EXISTS "Tasks tenant isolation" ON tasks;
-- DROP POLICY IF EXISTS "Notes tenant isolation" ON notes;
-- DROP POLICY IF EXISTS "Events tenant isolation" ON events;
-- DROP POLICY IF EXISTS "Audit logs tenant isolation" ON audit_logs;
-- DROP POLICY IF EXISTS "Departments tenant isolation" ON departments;
-- DROP POLICY IF EXISTS "Employees tenant isolation" ON employees;
-- DROP POLICY IF EXISTS "Locations tenant isolation" ON locations;
-- DROP POLICY IF EXISTS "Meeting rooms tenant isolation" ON meeting_rooms;
-- DROP POLICY IF EXISTS "Room bookings tenant isolation" ON room_bookings;
-- DROP POLICY IF EXISTS "Customers tenant isolation" ON customers;
-- DROP POLICY IF EXISTS "Appointments tenant isolation" ON appointments;
-- DROP POLICY IF EXISTS "Time entries tenant isolation" ON time_entries;
-- DROP POLICY IF EXISTS "Attendance tenant isolation" ON attendances;
