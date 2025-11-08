"""Supabase database client initialization"""
from supabase import create_client, Client
from app.config import settings

# Initialize Supabase client
supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_ROLE_KEY
)

# Public client for user operations (uses anon key)
supabase_public: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

