-- LifeFlow Phase 3 Database Schema
-- Run this migration in your Supabase SQL editor

-- Notifications table (stores micro-nudges and other notifications)
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES raw_tasks(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES daily_plans(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL DEFAULT 'nudge',
    message TEXT NOT NULL,
    scheduled_at TIMESTAMPTZ NOT NULL,
    sent_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'dismissed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task feedback table (stores user actions: done/snoozed)
CREATE TABLE IF NOT EXISTS task_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    task_id UUID NOT NULL REFERENCES raw_tasks(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES daily_plans(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('done', 'snoozed')),
    snooze_duration_minutes INTEGER,
    feedback_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_task_id ON notifications(task_id);
CREATE INDEX IF NOT EXISTS idx_notifications_plan_id ON notifications(plan_id);
CREATE INDEX IF NOT EXISTS idx_notifications_scheduled_at ON notifications(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_status ON notifications(user_id, status);

CREATE INDEX IF NOT EXISTS idx_task_feedback_user_id ON task_feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_task_feedback_task_id ON task_feedback(task_id);
CREATE INDEX IF NOT EXISTS idx_task_feedback_plan_id ON task_feedback(plan_id);
CREATE INDEX IF NOT EXISTS idx_task_feedback_action ON task_feedback(action);
CREATE INDEX IF NOT EXISTS idx_task_feedback_feedback_at ON task_feedback(feedback_at);

-- Triggers to automatically update updated_at
CREATE TRIGGER update_notifications_updated_at
    BEFORE UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_feedback ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own notifications
CREATE POLICY "Users can view own notifications"
    ON notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own notifications"
    ON notifications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own notifications"
    ON notifications FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own notifications"
    ON notifications FOR DELETE
    USING (auth.uid() = user_id);

-- Policy: Users can only access their own task feedback
CREATE POLICY "Users can view own task feedback"
    ON task_feedback FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own task feedback"
    ON task_feedback FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own task feedback"
    ON task_feedback FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own task feedback"
    ON task_feedback FOR DELETE
    USING (auth.uid() = user_id);

