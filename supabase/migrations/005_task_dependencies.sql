-- LifeFlow Phase 1, Version 2, Step 3: Task Dependencies
-- Create task dependencies table to model blocking relationships between tasks

-- Task dependencies table
CREATE TABLE IF NOT EXISTS task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID NOT NULL REFERENCES raw_tasks(id) ON DELETE CASCADE,
    blocked_by_task_id UUID NOT NULL REFERENCES raw_tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) NOT NULL DEFAULT 'blocks' CHECK (dependency_type IN ('blocks', 'depends_on', 'related_to')),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure a task cannot block itself
    CONSTRAINT task_cannot_block_itself CHECK (task_id != blocked_by_task_id),
    
    -- Ensure unique dependency relationships
    CONSTRAINT unique_dependency UNIQUE (task_id, blocked_by_task_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_dependencies_task_id ON task_dependencies(task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_blocked_by_task_id ON task_dependencies(blocked_by_task_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_user_id ON task_dependencies(user_id);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_dependency_type ON task_dependencies(dependency_type);

-- Function to check for circular dependencies
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
DECLARE
    circular_check BOOLEAN;
BEGIN
    -- Check if adding this dependency would create a circular reference
    -- This uses a recursive CTE to detect cycles
    WITH RECURSIVE dependency_chain AS (
        -- Start with the new dependency
        SELECT NEW.task_id as current_task, NEW.blocked_by_task_id as blocking_task, 1 as depth
        UNION ALL
        -- Follow the chain of dependencies
        SELECT td.task_id, td.blocked_by_task_id, dc.depth + 1
        FROM task_dependencies td
        JOIN dependency_chain dc ON td.task_id = dc.blocking_task
        WHERE dc.depth < 100  -- Prevent infinite loops
    )
    SELECT EXISTS(
        SELECT 1 FROM dependency_chain 
        WHERE current_task = NEW.blocked_by_task_id 
        AND blocking_task = NEW.task_id
    ) INTO circular_check;
    
    IF circular_check THEN
        RAISE EXCEPTION 'Circular dependency detected: Task % cannot block task % because it would create a cycle', NEW.task_id, NEW.blocked_by_task_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent circular dependencies
CREATE TRIGGER prevent_circular_dependency
    BEFORE INSERT OR UPDATE ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION check_circular_dependency();

-- Function to update updated_at timestamp (if needed in future)
CREATE OR REPLACE FUNCTION update_task_dependencies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.created_at = COALESCE(NEW.created_at, NOW());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to set created_at if not provided
CREATE TRIGGER set_task_dependencies_created_at
    BEFORE INSERT ON task_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION update_task_dependencies_updated_at();

-- Row Level Security (RLS) Policies
ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view their own task dependencies
CREATE POLICY "Users can view own task dependencies"
    ON task_dependencies FOR SELECT
    USING (auth.uid() = user_id);

-- Policy: Users can insert their own task dependencies
CREATE POLICY "Users can insert own task dependencies"
    ON task_dependencies FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own task dependencies
CREATE POLICY "Users can update own task dependencies"
    ON task_dependencies FOR UPDATE
    USING (auth.uid() = user_id);

-- Policy: Users can delete their own task dependencies
CREATE POLICY "Users can delete own task dependencies"
    ON task_dependencies FOR DELETE
    USING (auth.uid() = user_id);

