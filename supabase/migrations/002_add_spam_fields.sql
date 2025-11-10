-- Migration: Add spam detection fields to raw_tasks table
-- This migration adds fields to track spam detection for email-derived tasks

-- Add spam detection fields
ALTER TABLE raw_tasks
ADD COLUMN IF NOT EXISTS is_spam BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS spam_reason TEXT,
ADD COLUMN IF NOT EXISTS spam_score REAL;

-- Add index on is_spam for filtering queries
CREATE INDEX IF NOT EXISTS idx_raw_tasks_is_spam ON raw_tasks(is_spam) WHERE is_spam = TRUE;

-- Add comment to document the fields
COMMENT ON COLUMN raw_tasks.is_spam IS 'Indicates if the task was identified as spam/promotional email';
COMMENT ON COLUMN raw_tasks.spam_reason IS 'Reason for spam detection (e.g., "Gmail CATEGORY_PROMOTIONS label", "Promotional domain pattern")';
COMMENT ON COLUMN raw_tasks.spam_score IS 'Confidence score for spam detection (0.0-1.0)';

