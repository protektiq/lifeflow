-- LifeFlow Task Completion Tracking Migration
-- Adds completion tracking fields to raw_tasks table for analytics

-- Add completion tracking fields to raw_tasks table
ALTER TABLE raw_tasks 
ADD COLUMN IF NOT EXISTS is_completed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

-- Create index for performance on completion queries
CREATE INDEX IF NOT EXISTS idx_raw_tasks_is_completed ON raw_tasks(is_completed);
CREATE INDEX IF NOT EXISTS idx_raw_tasks_completed_at ON raw_tasks(completed_at);
CREATE INDEX IF NOT EXISTS idx_raw_tasks_source_completed ON raw_tasks(source, is_completed);
CREATE INDEX IF NOT EXISTS idx_raw_tasks_priority_completed ON raw_tasks(extracted_priority, is_completed);

-- Create a function to automatically update completed_at when is_completed changes
CREATE OR REPLACE FUNCTION update_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_completed = TRUE AND OLD.is_completed = FALSE THEN
        NEW.completed_at = NOW();
    ELSIF NEW.is_completed = FALSE THEN
        NEW.completed_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically set completed_at
CREATE TRIGGER update_raw_tasks_completed_at
    BEFORE UPDATE OF is_completed ON raw_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_completed_at();

