-- LifeFlow Phase 2 Database Schema
-- Run this migration in your Supabase SQL editor

-- Daily energy levels table (tracks user's daily energy level input)
CREATE TABLE IF NOT EXISTS daily_energy_levels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    energy_level INTEGER NOT NULL CHECK (energy_level >= 1 AND energy_level <= 5),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Daily plans table (stores generated daily plans)
CREATE TABLE IF NOT EXISTS daily_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_date DATE NOT NULL,
    tasks JSONB NOT NULL DEFAULT '[]'::jsonb,
    energy_level INTEGER CHECK (energy_level >= 1 AND energy_level <= 5),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, plan_date)
);

-- Add critical and urgent flags to raw_tasks table
ALTER TABLE raw_tasks 
ADD COLUMN IF NOT EXISTS is_critical BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS is_urgent BOOLEAN DEFAULT FALSE;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_daily_energy_levels_user_id ON daily_energy_levels(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_energy_levels_date ON daily_energy_levels(date);
CREATE INDEX IF NOT EXISTS idx_daily_plans_user_id ON daily_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_plans_plan_date ON daily_plans(plan_date);
CREATE INDEX IF NOT EXISTS idx_daily_plans_status ON daily_plans(status);
CREATE INDEX IF NOT EXISTS idx_raw_tasks_critical ON raw_tasks(is_critical);
CREATE INDEX IF NOT EXISTS idx_raw_tasks_urgent ON raw_tasks(is_urgent);

-- Triggers to automatically update updated_at
CREATE TRIGGER update_daily_energy_levels_updated_at
    BEFORE UPDATE ON daily_energy_levels
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_daily_plans_updated_at
    BEFORE UPDATE ON daily_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE daily_energy_levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_plans ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own daily energy levels
CREATE POLICY "Users can view own daily energy levels"
    ON daily_energy_levels FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own daily energy levels"
    ON daily_energy_levels FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own daily energy levels"
    ON daily_energy_levels FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own daily energy levels"
    ON daily_energy_levels FOR DELETE
    USING (auth.uid() = user_id);

-- Policy: Users can only access their own daily plans
CREATE POLICY "Users can view own daily plans"
    ON daily_plans FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own daily plans"
    ON daily_plans FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own daily plans"
    ON daily_plans FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own daily plans"
    ON daily_plans FOR DELETE
    USING (auth.uid() = user_id);

