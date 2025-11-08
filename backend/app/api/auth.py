"""Authentication API endpoints"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Login failed: {str(e)}",
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
async def google_authorize():
    """Initiate Google OAuth flow"""
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow = get_google_flow(redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    
    # Store state in session/cookie (simplified - in production use proper session management)
    return {"url": authorization_url, "state": state}


@router.get("/google/callback")
async def google_callback(code: str, state: Optional[str] = None):
    """Handle Google OAuth callback"""
    try:
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        flow = get_google_flow(redirect_uri)
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Get user info from Google
        service = build('oauth2', 'v2', credentials=credentials)
        user_info = service.userinfo().get().execute()
        google_email = user_info.get('email')

        # Find or create user in Supabase
        # Note: This is simplified - in production, you'd want to link Google account to existing user
        # or create a new user account
        
        # For now, we'll need the user to be authenticated first
        # This endpoint should be called after user is logged in
        # We'll store the OAuth tokens for the authenticated user
        
        return RedirectResponse(
            url=f"{settings.CORS_ORIGINS[0]}/dashboard?google_connected=true"
        )
    except Exception as e:
        return RedirectResponse(
            url=f"{settings.CORS_ORIGINS[0]}/dashboard?error={str(e)}"
        )


def get_current_user(token: str):
    """Validate JWT token and return user"""
    try:
        # Verify token with Supabase
        response = supabase.auth.get_user(token)
        return response.user
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

