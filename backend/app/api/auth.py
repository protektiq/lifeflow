"""Authentication API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.database import supabase, supabase_public
from app.config import settings
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import json
from datetime import datetime, timedelta
import secrets

router = APIRouter()

# Google OAuth flow
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
CLIENT_SECRETS_FILE = None  # We'll use client ID/secret from env


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def get_google_flow(redirect_uri: str) -> Flow:
    """Create Google OAuth flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    return flow


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Email/password login"""
    try:
        # Use Supabase Auth for email/password login
        response = supabase_public.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password,
        })

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        # Get or create user profile
        profile_response = supabase.table("user_profiles").select("*").eq("user_id", response.user.id).execute()
        
        if not profile_response.data:
            # Create profile if it doesn't exist
            supabase.table("user_profiles").insert({
                "user_id": response.user.id,
                "energy_level": None,
                "preferences": {},
            }).execute()

        return TokenResponse(
            access_token=response.session.access_token,
            user={
                "id": response.user.id,
                "email": response.user.email,
            },
        )
    except Exception as e:
        # Extract more detailed error message from Supabase
        error_message = str(e)
        if hasattr(e, 'message'):
            error_message = e.message
        elif hasattr(e, 'args') and len(e.args) > 0:
            error_message = str(e.args[0])
        
        # Check for common Supabase errors
        if "email" in error_message.lower() and "confirm" in error_message.lower():
            error_message = "Please confirm your email address before signing in. Check your inbox for a confirmation email."
        elif "invalid" in error_message.lower() or "credentials" in error_message.lower():
            error_message = "Invalid email or password"
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {error_message}",
        )


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """User registration"""
    try:
        # Use Supabase Auth for registration
        response = supabase_public.auth.sign_up({
            "email": request.email,
            "password": request.password,
        })

        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed",
            )

        # Create user profile
        supabase.table("user_profiles").insert({
            "user_id": response.user.id,
            "energy_level": None,
            "preferences": {},
        }).execute()

        return TokenResponse(
            access_token=response.session.access_token if response.session else "",
            user={
                "id": response.user.id,
                "email": response.user.email,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration failed: {str(e)}",
        )


@router.get("/google/authorize")
async def google_authorize(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())
):
    """Initiate Google OAuth flow - requires authentication"""
    try:
        # Get authenticated user
        user = get_current_user(credentials.credentials)
        user_id = user.id
        
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow = get_google_flow(redirect_uri)
        
        # Generate state and encode user_id in it
        import base64
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
        )
        # Append encoded user_id to state
        encoded_user_id = base64.urlsafe_b64encode(user_id.encode()).decode()
        authorization_url = authorization_url.replace(f"state={state}", f"state={state}:{encoded_user_id}")
        
        return {"url": authorization_url, "state": f"{state}:{encoded_user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication required: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(code: str, state: Optional[str] = None):
    """Handle Google OAuth callback"""
    try:
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow = get_google_flow(redirect_uri)
        
        # Extract user_id from state if present (format: "state:encoded_user_id")
        user_id = None
        if state and ':' in state:
            parts = state.split(':', 1)
            if len(parts) == 2:
                import base64
                try:
                    user_id = base64.urlsafe_b64decode(parts[1].encode()).decode()
                except Exception:
                    pass  # If decoding fails, user_id stays None
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Validate that we have user_id from state
        if not user_id:
            return RedirectResponse(
                url=f"{settings.CORS_ORIGINS[0]}/dashboard?error=user_id_required_please_reconnect"
            )
        
        # Store OAuth tokens
        from app.agents.perception.calendar_ingestion import store_oauth_tokens
        
        access_token = credentials.token
        refresh_token = credentials.refresh_token
        expires_in = None
        if credentials.expiry:
            expires_in = int((credentials.expiry - datetime.utcnow()).total_seconds())
        
        # Store tokens
        try:
            await store_oauth_tokens(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=expires_in
            )
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"OAuth tokens stored successfully for user {user_id}")
        except Exception as storage_error:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to store OAuth tokens: {str(storage_error)}")
            return RedirectResponse(
                url=f"{settings.CORS_ORIGINS[0]}/dashboard?error=token_storage_failed"
            )
        
        return RedirectResponse(
            url=f"{settings.CORS_ORIGINS[0]}/dashboard?google_connected=true"
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"OAuth callback error: {str(e)}")
        return RedirectResponse(
            url=f"{settings.CORS_ORIGINS[0]}/dashboard?error={str(e)}"
        )


def get_current_user(token: str):
    """Validate JWT token and return user"""
    try:
        # Verify token with Supabase using public client
        # get_user validates the JWT token and returns the user
        response = supabase_public.auth.get_user(token)
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
        return response.user
    except HTTPException:
        raise
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

