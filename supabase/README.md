# Supabase Setup Instructions

Complete guide for setting up Supabase database, authentication, and migrations for LifeFlow.

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Create a new project
3. Note down your project URL and API keys:
   - Project URL (SUPABASE_URL)
   - Anon/Public Key (SUPABASE_KEY)
   - Service Role Key (SUPABASE_SERVICE_ROLE_KEY)

## 2. Run Database Migrations

**Important**: Run migrations in the correct order as they build upon each other.

1. Open your Supabase project dashboard
2. Go to **SQL Editor**
3. Run each migration file **sequentially** in this order:

### Migration Order

1. **`001_initial_schema.sql`** - Core tables (user_profiles, oauth_tokens, raw_tasks)
   - Creates base tables for users, OAuth tokens, and tasks
   - Sets up Row Level Security (RLS) policies
   - Creates indexes for performance

2. **`002_phase2_schema.sql`** - Daily plans and energy levels
   - Creates `daily_energy_levels` table
   - Creates `daily_plans` table
   - Adds critical/urgent flags to `raw_tasks` table
   - Sets up RLS policies

3. **`002_task_manager_sync.sql`** - Task manager sync support
   - Adds sync tracking columns to `raw_tasks` table
   - Creates indexes for sync operations
   - Supports bidirectional sync with external task managers

4. **`002_add_spam_fields.sql`** - Spam detection fields (if applicable)
   - Adds spam detection columns to `raw_tasks` table

5. **`003_phase3_notifications.sql`** - Notifications and reminders
   - Creates `notifications` table
   - Creates `task_feedback` table
   - Creates `reminders` table
   - Sets up RLS policies and indexes

6. **`004_get_user_email_function.sql`** - Email lookup function
   - Creates helper function to get user email from auth.users
   - Used for email notifications

### Running Migrations

For each migration file:

1. Open the migration file in your editor
2. Copy the entire contents
3. Paste into Supabase SQL Editor
4. Click **Run** or press `Ctrl+Enter` (Windows/Linux) or `Cmd+Enter` (Mac)
5. Verify the migration completed successfully
6. Move to the next migration

> ⚠️ **Warning**: Do not skip migrations or run them out of order. Each migration builds upon the previous ones.

## 3. Configure Authentication Providers

### Email/Password Authentication

1. Go to **Authentication > Providers** in Supabase dashboard
2. Enable **Email** provider
3. Configure email templates if needed (optional)
4. Set up email confirmation settings (recommended for production)

### Google OAuth

1. Go to **Authentication > Providers** in Supabase dashboard
2. Enable **Google** provider
3. Add your Google OAuth credentials:
   - **Client ID** (from Google Cloud Console)
   - **Client Secret** (from Google Cloud Console)
4. Add authorized redirect URLs:
   - `http://localhost:3000/auth/callback` (development - frontend)
   - `http://localhost:8000/api/auth/google/callback` (development - backend)
   - Your production callback URLs (when deployed)

## 4. Google Cloud Console Setup

To get Google OAuth credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. **Enable Google Calendar API**:
   - Go to **APIs & Services > Library**
   - Search for "Google Calendar API"
   - Click **Enable**
4. **Configure OAuth Consent Screen**:
   - Go to **APIs & Services > OAuth consent screen**
   - Choose **External** (unless you have a Google Workspace)
   - Fill in required information (app name, user support email, etc.)
   - Add scopes: `https://www.googleapis.com/auth/calendar.readonly`
   - Add test users (for development)
5. **Create OAuth Credentials**:
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth 2.0 Client ID**
   - Choose **Web application**
   - Add authorized redirect URIs:
     - `http://localhost:3000/auth/callback` (frontend)
     - `http://localhost:8000/api/auth/google/callback` (backend)
     - Your production URLs
   - Click **Create**
6. **Copy Credentials**:
   - Copy the **Client ID** and **Client Secret**
   - Add them to your `.env` files (see below)

## 5. Environment Variables

### Backend `.env` File

Add these to your `backend/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Frontend `.env.local` File

Add these to your `frontend/.env.local`:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 6. Verify Setup

After completing the setup:

1. **Check Tables**: Go to **Table Editor** in Supabase dashboard and verify all tables exist:
   - `user_profiles`
   - `oauth_tokens`
   - `raw_tasks`
   - `daily_energy_levels`
   - `daily_plans`
   - `notifications`
   - `task_feedback`
   - `reminders`

2. **Check RLS Policies**: Go to **Authentication > Policies** and verify RLS is enabled on all tables

3. **Test Authentication**: Try signing up/logging in through the frontend

4. **Test OAuth**: Try connecting Google Calendar through the integrations page

## 7. Database Schema Overview

### Core Tables

- **`user_profiles`** - Extended user information (energy levels, preferences)
- **`oauth_tokens`** - OAuth tokens for Google Calendar access
- **`raw_tasks`** - Extracted tasks from calendar events

### Planning Tables

- **`daily_energy_levels`** - User's daily energy level inputs
- **`daily_plans`** - Generated daily plans with tasks

### Notification Tables

- **`notifications`** - Micro-nudges and notifications
- **`task_feedback`** - User feedback on tasks (done/snoozed)
- **`reminders`** - Task reminders

### Indexes

All tables have appropriate indexes for:
- User ID lookups
- Date/time queries
- Sync operations
- Status filtering

## 8. Row Level Security (RLS)

All tables have RLS enabled with policies that ensure:
- Users can only access their own data
- Users can insert/update/delete their own records
- Service role can access all data (for backend operations)

## 9. Troubleshooting

### Migration Errors

- **"relation already exists"**: Table already created, safe to skip
- **"column already exists"**: Column already added, safe to skip
- **"function already exists"**: Function already created, safe to skip

### Authentication Issues

- Verify OAuth credentials are correct
- Check redirect URIs match exactly (including trailing slashes)
- Ensure Google Calendar API is enabled
- Check OAuth consent screen is configured

### Permission Errors

- Verify RLS policies are created
- Check service role key is used for backend operations
- Ensure user is authenticated before accessing data

## 10. Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
- [Google OAuth Setup Guide](../GOOGLE_OAUTH_SETUP.md)
- [Environment Setup Guide](../ENV_SETUP.md)

---

**Made with ❤️ for LifeFlow**
