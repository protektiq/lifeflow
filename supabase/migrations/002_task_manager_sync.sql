-- LifeFlow Phase 2: Task Manager Sync Tracking
-- Add sync tracking fields to raw_tasks table for bidirectional sync support

-- Add sync tracking columns to raw_tasks table
ALTER TABLE raw_tasks
ADD COLUMN IF NOT EXISTS external_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS sync_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_direction VARCHAR(20) DEFAULT 'bidirectional',
ADD COLUMN IF NOT EXISTS external_updated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS sync_error TEXT;

-- Add check constraint for sync_status
ALTER TABLE raw_tasks
ADD CONSTRAINT check_sync_status 
CHECK (sync_status IN ('synced', 'pending', 'conflict', 'error') OR sync_status IS NULL);

-- Add check constraint for sync_direction
ALTER TABLE raw_tasks
ADD CONSTRAINT check_sync_direction 
CHECK (sync_direction IN ('inbound', 'outbound', 'bidirectional') OR sync_direction IS NULL);

-- Create index for efficient lookups by external_id and source
CREATE INDEX IF NOT EXISTS idx_raw_tasks_external_id ON raw_tasks(source, external_id) 
WHERE external_id IS NOT NULL;

-- Create index for sync status queries
CREATE INDEX IF NOT EXISTS idx_raw_tasks_sync_status ON raw_tasks(user_id, sync_status) 
WHERE sync_status IS NOT NULL;

-- Create index for sync operations
CREATE INDEX IF NOT EXISTS idx_raw_tasks_last_synced ON raw_tasks(user_id, last_synced_at) 
WHERE last_synced_at IS NOT NULL;

