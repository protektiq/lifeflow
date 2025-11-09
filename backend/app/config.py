"""Application configuration and environment variables"""
from pydantic_settings import BaseSettings
from typing import List
import json
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/auth/google/callback"
    
    # OpenAI Configuration
    OPENAI_API_KEY: str
    
    # Chroma Configuration
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_db"  # Local storage directory
    CHROMA_MODE: str = "persistent"  # "persistent" or "http" (http requires separate server)
    
    # Database Configuration
    DATABASE_URL: str = ""
    
    # CORS Configuration - can be set as JSON array string in env var
    # Default values work for local development
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse CORS_ORIGINS from environment variable if set (for production deployments)
        # This only runs if CORS_ORIGINS is explicitly set as an env var, not from .env file
        # Local development uses default values or .env file, which pydantic handles normally
        cors_env = os.getenv("CORS_ORIGINS")
        if cors_env:
            # Check if it looks like JSON (starts with [) or comma-separated
            cors_env = cors_env.strip()
            if cors_env.startswith("[") or cors_env.startswith('['):
                # Try parsing as JSON array
                try:
                    parsed = json.loads(cors_env)
                    if isinstance(parsed, list):
                        self.CORS_ORIGINS = parsed
                except (json.JSONDecodeError, ValueError):
                    pass  # Fall back to pydantic's parsed value
            elif "," in cors_env:
                # Try parsing as comma-separated string
                self.CORS_ORIGINS = [origin.strip() for origin in cors_env.split(",") if origin.strip()]
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_ENABLED: bool = False
    
    # Application Configuration
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

