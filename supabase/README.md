# Supabase Setup Instructions

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Create a new project
3. Note down your project URL and API keys:
   - Project URL (SUPABASE_URL)
   - Anon/Public Key (SUPABASE_KEY)
   - Service Role Key (SUPABASE_SERVICE_ROLE_KEY)

## 2. Run Database Migration

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Copy and paste the contents of `migrations/001_initial_schema.sql`
4. Run the migration

## 3. Configure Authentication Providers

### Email/Password Authentication
1. Go to Authentication > Providers
2. Enable Email provider
3. Configure email templates if needed

### Google OAuth
1. Go to Authentication > Providers
2. Enable Google provider
3. Add your Google OAuth credentials:
   - Client ID (from Google Cloud Console)
   - Client Secret (from Google Cloud Console)
4. Add authorized redirect URLs:
   - `http://localhost:8000/api/auth/google/callback` (development)
   - Your production callback URL (when deployed)

## 4. Google Cloud Console Setup

To get Google OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Go to Credentials > Create Credentials > OAuth 2.0 Client ID
5. Configure OAuth consent screen
6. Create OAuth client ID for Web application
7. Add authorized redirect URIs:
   - `http://localhost:8000/api/auth/google/callback` (development)
   - Your production callback URL
8. Copy Client ID and Client Secret to your `.env` files

## 5. Environment Variables

Add these to your backend `.env`:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

Add these to your frontend `.env.local`:
```
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

