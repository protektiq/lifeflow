-- LifeFlow Phase 3: Function to get user email
-- This function allows retrieving user email from auth.users table

CREATE OR REPLACE FUNCTION get_user_email(user_uuid UUID)
RETURNS TEXT AS $$
DECLARE
    user_email TEXT;
BEGIN
    SELECT email INTO user_email
    FROM auth.users
    WHERE id = user_uuid;
    
    RETURN user_email;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to authenticated users (via service role)
-- Note: This function uses SECURITY DEFINER to bypass RLS

