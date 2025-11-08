# Environment Variables Setup Guide

This guide explains what environment variables need to be set for both the backend and frontend.

## Backend `.env` File

Create a `.env` file in the `backend/` directory with the following variables:

```bash
# ============================================
# Supabase Configuration (REQUIRED)
# ============================================
# Get these from your Supabase project dashboard:
# Project Settings > API > Project URL and API keys
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-public-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# ============================================
# Google OAuth Configuration (REQUIRED)
# ============================================
# Get these from Google Cloud Console:
# APIs & Services > Credentials > OAuth 2.0 Client ID
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

# ============================================
# OpenAI Configuration (REQUIRED)
# ============================================
# Get this from OpenAI platform: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# ============================================
# Chroma Vector Database Configuration
# ============================================
# Default values work for local Chroma instance
# Change if using remote Chroma server
CHROMA_HOST=localhost
CHROMA_PORT=8000

# ============================================
# Database Configuration (OPTIONAL)
# ============================================
# Only needed if using direct PostgreSQL connection
# Otherwise, Supabase handles database connections
DATABASE_URL=

# ============================================
# CORS Configuration
# ============================================
# Comma-separated list of allowed origins
# Add your production frontend URL when deploying
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# ============================================
# Application Configuration
# ============================================
ENVIRONMENT=development
DEBUG=true
```

## Frontend `.env.local` File

Create a `.env.local` file in the `frontend/` directory with the following variables:

```bash
# ============================================
# Supabase Configuration (REQUIRED)
# ============================================
# Get these from your Supabase project dashboard:
# Project Settings > API > Project URL and API keys
# Use the ANON/PUBLIC key (not the service role key!)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-public-key-here

# ============================================
# FastAPI Backend URL (REQUIRED)
# ============================================
# URL where your FastAPI backend is running
# Change to your production backend URL when deploying
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Where to Get Each Value

### Supabase Values

1. Go to [supabase.com](https://supabase.com) and sign in
2. Create a new project or select existing one
3. Go to **Project Settings** > **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY` (backend) and `NEXT_PUBLIC_SUPABASE_ANON_KEY` (frontend)
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY` (backend only - keep secret!)

### Google OAuth Values

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable **Google Calendar API**:
   - Go to **APIs & Services** > **Library**
   - Search for "Google Calendar API"
   - Click **Enable**
4. Configure OAuth Consent Screen:
   - Go to **APIs & Services** > **OAuth consent screen**
   - Fill in required information
   - Add your email as a test user (for development)
5. Create OAuth 2.0 Credentials:
   - Go to **APIs & Services** > **Credentials**
   - Click **Create Credentials** > **OAuth 2.0 Client ID**
   - Choose **Web application**
   - Add authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback` (development)
     - Your production callback URL (when deployed)
   - Copy:
     - **Client ID** → `GOOGLE_CLIENT_ID`
     - **Client Secret** → `GOOGLE_CLIENT_SECRET`

### OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign in or create an account
3. Go to **API Keys** section
4. Click **Create new secret key**
5. Copy the key → `OPENAI_API_KEY`
   - ⚠️ **Important**: The key starts with `sk-` and you can only see it once!

### Chroma Configuration

- **Default values** (`localhost:8000`) work if running Chroma locally
- If using Chroma Cloud or a remote instance, update `CHROMA_HOST` and `CHROMA_PORT` accordingly
- For local development, you can install Chroma: `pip install chromadb` and it runs automatically

## Security Notes

⚠️ **IMPORTANT SECURITY REMINDERS:**

1. **Never commit `.env` or `.env.local` files to git** - They're already in `.gitignore`
2. **Service Role Key** (`SUPABASE_SERVICE_ROLE_KEY`) is highly sensitive - only use in backend
3. **OpenAI API Key** is sensitive - keep it secret
4. **Google Client Secret** should be kept private
5. Use different keys for development and production
6. Rotate keys if they're accidentally exposed

## Quick Setup Checklist

- [ ] Create Supabase project
- [ ] Get Supabase URL and keys
- [ ] Create Google Cloud project
- [ ] Enable Google Calendar API
- [ ] Create Google OAuth credentials
- [ ] Get OpenAI API key
- [ ] Create `backend/.env` file with all values
- [ ] Create `frontend/.env.local` file with all values
- [ ] Verify all values are correct (no extra spaces, quotes, etc.)

## Example Files

You can copy the example files and fill in your values:

```bash
# Backend
cd backend
cp .env.example .env  # If .env.example exists, otherwise create .env manually
# Edit .env with your values

# Frontend
cd frontend
cp .env.local.example .env.local  # If .env.local.example exists, otherwise create .env.local manually
# Edit .env.local with your values
```

## Troubleshooting

- **"Missing environment variable" errors**: Check that all required variables are set
- **CORS errors**: Verify `CORS_ORIGINS` includes your frontend URL
- **Google OAuth errors**: Check redirect URI matches exactly in Google Console
- **Supabase connection errors**: Verify URL and keys are correct (no extra spaces)

