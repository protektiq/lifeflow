"""Supabase database client initialization"""
from supabase import create_client, Client
from app.config import settings
from typing import Optional

# Lazy initialization - clients will be created on first access
_supabase_client: Optional[Client] = None
_supabase_public_client: Optional[Client] = None


def _validate_supabase_config():
    """Validate that Supabase configuration is not using placeholder values"""
    placeholder_values = [
        "your_supabase_project_url",
        "your_supabase_anon_key",
        "your_supabase_service_role_key"
    ]
    
    errors = []
    
    if settings.SUPABASE_URL in placeholder_values or not settings.SUPABASE_URL.startswith(('http://', 'https://')):
        errors.append("SUPABASE_URL")
    
    if settings.SUPABASE_KEY in placeholder_values or len(settings.SUPABASE_KEY) < 20:
        errors.append("SUPABASE_KEY")
    
    if settings.SUPABASE_SERVICE_ROLE_KEY in placeholder_values or len(settings.SUPABASE_SERVICE_ROLE_KEY) < 20:
        errors.append("SUPABASE_SERVICE_ROLE_KEY")
    
    if errors:
        error_msg = (
            "Supabase configuration is incomplete. The following environment variables need to be configured:\n"
            f"  - {', '.join(errors)}\n\n"
            "Please update your .env file with valid values.\n"
            "Get your Supabase credentials from: https://app.supabase.com/project/_/settings/api\n\n"
            "Required values:\n"
            "  - SUPABASE_URL: Your Supabase project URL (e.g., https://xxxxx.supabase.co)\n"
            "  - SUPABASE_KEY: Your Supabase anon/public key\n"
            "  - SUPABASE_SERVICE_ROLE_KEY: Your Supabase service role key (keep this secret!)"
        )
        raise ValueError(error_msg)


def _get_supabase_client() -> Client:
    """Get or create the Supabase service role client"""
    global _supabase_client
    if _supabase_client is None:
        _validate_supabase_config()
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    return _supabase_client


def _get_supabase_public_client() -> Client:
    """Get or create the Supabase public (anon key) client"""
    global _supabase_public_client
    if _supabase_public_client is None:
        _validate_supabase_config()
        _supabase_public_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
    return _supabase_public_client


# Provide backward-compatible interface using properties
class SupabaseClients:
    """Wrapper class to provide lazy-loaded Supabase clients"""
    
    @property
    def supabase(self) -> Client:
        return _get_supabase_client()
    
    @property
    def supabase_public(self) -> Client:
        return _get_supabase_public_client()


# Create singleton instance
_clients = SupabaseClients()

# Export clients with backward-compatible names
# These will be accessed as properties, triggering lazy initialization
def __getattr__(name: str):
    if name == "supabase":
        return _get_supabase_client()
    elif name == "supabase_public":
        return _get_supabase_public_client()
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

