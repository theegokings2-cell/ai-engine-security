-- Migration: Add timezone column to users table
-- Run this to add user timezone support

-- Add timezone column with default 'UTC'
ALTER TABLE users ADD COLUMN timezone VARCHAR(50) NOT NULL DEFAULT 'UTC';

-- Update existing users to have UTC timezone
UPDATE users SET timezone = 'UTC' WHERE timezone IS NULL OR timezone = '';

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_timezone ON users(timezone);

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'timezone';
