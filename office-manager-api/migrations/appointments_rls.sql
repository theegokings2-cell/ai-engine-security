-- Apply RLS to appointments table only
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Appointments tenant isolation" ON appointments
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Verify
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public' AND tablename = 'appointments';
SELECT policyname, tablename FROM pg_policies WHERE schemaname = 'public' AND tablename = 'appointments';
