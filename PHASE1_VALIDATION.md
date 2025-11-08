# Phase 1 Validation Guide

This guide walks you through completing the remaining validation steps for LifeFlow Phase 1.

## Prerequisites Checklist

- [x] Backend running on port 8000
- [x] Frontend running on port 3000
- [x] User account created and logged in
- [x] Authentication working (403 errors resolved)
- [ ] Google OAuth credentials configured
- [ ] Supabase migration executed
- [ ] Calendar sync tested
- [ ] Accuracy validated

---

## Step 1: Google OAuth Credentials Configuration

### 1.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click **"New Project"**
4. Enter project name: `LifeFlow` (or your preferred name)
5. Click **"Create"**
6. Wait for project creation, then select it

### 1.2 Enable Google Calendar API

1. In the Google Cloud Console, go to **"APIs & Services"** > **"Library"**
2. Search for **"Google Calendar API"**
3. Click on **"Google Calendar API"**
4. Click **"Enable"**
5. Wait for the API to be enabled

### 1.3 Configure OAuth Consent Screen

1. Go to **"APIs & Services"** > **"OAuth consent screen"**
2. Select **"External"** (unless you have a Google Workspace account)
3. Click **"Create"**
4. Fill in the required information:
   - **App name**: `LifeFlow`
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click **"Save and Continue"**
6. On **"Scopes"** page:
   - Click **"Add or Remove Scopes"**
   - Search for and select: `https://www.googleapis.com/auth/calendar.readonly`
   - Click **"Update"** > **"Save and Continue"**
7. On **"Test users"** page (for development):
   - Click **"Add Users"**
   - Add your email address
   - Click **"Add"** > **"Save and Continue"**
8. Review and **"Back to Dashboard"**

### 1.4 Create OAuth 2.0 Credentials

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"+ Create Credentials"** > **"OAuth 2.0 Client ID"**
3. Select application type: **"Web application"**
4. Name it: `LifeFlow Web Client`
5. Under **"Authorized JavaScript origins"**:
   - Click **"+ Add URI"**
   - Add: `http://localhost:8000` (no trailing slash, no path)
   - This is for the backend origin
6. Under **"Authorized redirect URIs"**:
   - Click **"+ Add URI"**
   - Add: `http://localhost:8000/api/auth/google/callback` (full callback path)
   - This is where Google redirects after authorization
7. Click **"Create"**
8. **IMPORTANT**: Copy these values immediately (you can't see them again):
   - **Client ID** (looks like: `123456789-abcdefg.apps.googleusercontent.com`)
   - **Client Secret** (looks like: `GOCSPX-abcdefghijklmnop`)

### 1.5 Add Credentials to Backend

1. Open `backend/.env` file
2. Replace the placeholder values:
   ```bash
   GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-actual-client-secret-here
   ```
3. Save the file
4. The backend will auto-reload (if using `--reload` flag)

### 1.6 Verify Configuration

1. Check backend logs - should see no errors about missing Google credentials
2. Test the OAuth endpoint:
   ```bash
   curl http://localhost:8000/api/auth/google/authorize
   ```
   Should return a JSON with a `url` field

---

## Step 2: Supabase Migration Execution

### 2.1 Access Supabase SQL Editor

1. Go to your Supabase project dashboard: https://supabase.com/dashboard
2. Select your project
3. Click on **"SQL Editor"** in the left sidebar
4. Click **"New query"**

### 2.2 Run the Migration

1. Open the migration file: `supabase/migrations/001_initial_schema.sql`
2. Copy **ALL** the contents of the file
3. Paste into the Supabase SQL Editor
4. Click **"Run"** (or press Ctrl+Enter)
5. Wait for execution to complete
6. You should see: **"Success. No rows returned"**

### 2.3 Verify Tables Were Created

1. In Supabase dashboard, go to **"Table Editor"**
2. You should see these tables:
   - `user_profiles`
   - `oauth_tokens`
   - `raw_tasks`
3. Click on each table to verify the schema matches:
   - Check columns exist
   - Check indexes exist
   - Check RLS policies are enabled

### 2.4 Verify RLS Policies

1. In **"Table Editor"**, click on `raw_tasks` table
2. Click on **"Policies"** tab
3. You should see policies like:
   - "Users can view own raw tasks"
   - "Users can insert own raw tasks"
   - etc.
4. Repeat for `user_profiles` and `oauth_tokens` tables

---

## Step 3: Connect Google Calendar (OAuth Flow)

### 3.1 Initiate OAuth Flow from Frontend

**Option A: Using the Dashboard (if Google OAuth button is implemented)**
1. Go to `http://localhost:3000/dashboard`
2. Look for a "Connect Google Calendar" button
3. Click it
4. You'll be redirected to Google's consent screen

**Option B: Using the API directly**
1. Open browser and go to:
   ```
   http://localhost:8000/api/auth/google/authorize
   ```
2. Copy the `url` from the JSON response
3. Open that URL in your browser
4. Sign in with your Google account
5. Grant permissions for Calendar access
6. You'll be redirected back to the callback URL

### 3.2 Complete OAuth Flow

1. After clicking "Allow" on Google's consent screen
2. You'll be redirected to: `http://localhost:8000/api/auth/google/callback?code=...`
3. The backend should:
   - Exchange the code for tokens
   - Store tokens in `oauth_tokens` table
   - Redirect you to the dashboard

### 3.3 Verify OAuth Tokens Stored

1. In Supabase dashboard, go to **"Table Editor"**
2. Open `oauth_tokens` table
3. You should see a row with:
   - Your `user_id`
   - `provider` = "google"
   - `access_token` (encrypted/stored)
   - `refresh_token` (if provided)
   - `token_expires_at`

---

## Step 4: Test Calendar Sync

### 4.1 Ensure You Have Calendar Events

1. Go to [Google Calendar](https://calendar.google.com)
2. Make sure you have at least 50 events in your calendar
3. If you don't have enough events, you can:
   - Create test events manually
   - Import a calendar with events
   - Use Google Calendar's "Create event" feature

### 4.2 Trigger Calendar Sync

**Option A: From Dashboard UI**
1. Go to `http://localhost:3000/dashboard`
2. Click the **"Sync Calendar"** button
3. Wait for the sync to complete
4. Check for success message or error

**Option B: Using API Directly**
```bash
# Get your auth token first (from browser localStorage or Supabase session)
curl -X POST http://localhost:8000/api/ingestion/calendar/sync \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json"
```

### 4.3 Monitor Backend Logs

Watch your backend terminal for:
- Authentication node execution
- Calendar ingestion progress
- NLP extraction results
- Storage operations
- Any errors

Expected log flow:
```
workflow_auth_start - Starting authentication node
workflow_ingestion_start - Starting calendar ingestion
calendar_events_fetched - Fetched X events from Google Calendar
workflow_extraction_start - Starting NLP extraction
workflow_storage_start - Starting storage of raw tasks
workflow_storage_complete - Stored X raw tasks
```

### 4.4 Verify Tasks in Database

1. In Supabase dashboard, go to **"Table Editor"**
2. Open `raw_tasks` table
3. You should see rows with:
   - Your `user_id`
   - `source` = "google_calendar"
   - `title`, `start_time`, `end_time`, etc.
   - `raw_data` (JSON with original event data)

### 4.5 Verify Tasks in Dashboard

1. Refresh `http://localhost:3000/dashboard`
2. Scroll to the "Raw Tasks" section
3. You should see a list of your calendar events
4. Each task should show:
   - Title
   - Date/time
   - Location (if available)
   - Attendees count
   - Priority (if extracted)

---

## Step 5: Accuracy Validation (95% Target)

### 5.1 Count Total Events Synced

1. In Supabase, run this query in SQL Editor:
   ```sql
   SELECT COUNT(*) as total_tasks
   FROM raw_tasks
   WHERE user_id = 'YOUR_USER_ID_HERE';
   ```
   Replace `YOUR_USER_ID_HERE` with your actual user ID (from `user_profiles` table)

2. Note the count - this is your **total ingested events**

### 5.2 Sample Validation (Manual Check)

1. Pick a random sample of 20 events from your Google Calendar
2. For each event, check if it exists in `raw_tasks` table
3. Verify these fields are correct:
   - **Title** - Should match exactly
   - **Start time** - Should match (within timezone conversion)
   - **End time** - Should match
   - **Attendees** - Should include all attendees
   - **Location** - Should match if present
   - **Description** - Should match if present

### 5.3 Calculate Accuracy

**Accuracy Formula:**
```
Accuracy = (Correctly Extracted Fields / Total Fields Checked) × 100%
```

**Example:**
- Checked 20 events
- Each event has 5 fields (title, start_time, end_time, attendees, location)
- Total fields: 20 × 5 = 100 fields
- Found 95 fields correct
- Accuracy: 95/100 = 95% ✅

### 5.4 Check for Common Issues

**Missing Events:**
- Check if events were filtered out (cancelled events are skipped)
- Check date range (only events within last 30 days to next 90 days are fetched)
- Check for errors in backend logs

**Incorrect Data:**
- Timezone issues (check `start_time` and `end_time` formatting)
- Attendee extraction (check if emails are captured)
- Priority extraction (check if priority keywords are detected)

**Duplicate Events:**
- Check if same event appears multiple times
- Backend has deduplication logic, but verify it's working

### 5.5 Review Backend Metrics

1. Check the health endpoint:
   ```bash
   curl http://localhost:8000/api/health
   ```
2. Look at the `metrics` section:
   - `success_rate` - Should be close to 100%
   - `total_events` - Should match your calendar event count
   - `successful_ingestions` - Should be high
   - `failed_ingestions` - Should be low or zero

### 5.6 Check Ingestion Logs

Look for these log entries:
- `calendar_events_fetched` - Shows how many events were fetched
- `workflow_storage_complete` - Shows how many were stored
- `task_extraction_error` - Shows any extraction failures
- `task_storage_error` - Shows any storage failures

---

## Troubleshooting Common Issues

### Issue: OAuth Redirect URI Mismatch

**Error**: "redirect_uri_mismatch"

**Solution**:
1. Check Google Cloud Console > Credentials
2. Verify redirect URI exactly matches: `http://localhost:8000/api/auth/google/callback`
3. No trailing slashes, exact match required

### Issue: Calendar API Not Enabled

**Error**: "API not enabled"

**Solution**:
1. Go to Google Cloud Console > APIs & Services > Library
2. Search for "Google Calendar API"
3. Click "Enable"

### Issue: No Events Retrieved

**Possible Causes**:
- Date range too narrow (check `calendar_ingestion.py` - defaults to last 30 days to next 90 days)
- Calendar is empty
- OAuth token expired (check `oauth_tokens` table)

**Solution**:
1. Check backend logs for specific error
2. Verify OAuth tokens are valid
3. Check date range in code

### Issue: Low Accuracy (< 95%)

**Common Causes**:
- Timezone conversion errors
- Attendee extraction failing
- Description parsing issues
- Recurring event handling

**Solution**:
1. Review `nlp_extraction.py` logic
2. Check sample events that failed
3. Add more robust parsing for edge cases
4. Improve error handling

### Issue: Database Migration Errors

**Error**: "relation already exists" or similar

**Solution**:
1. Check if tables already exist in Supabase
2. Either drop existing tables or modify migration to use `IF NOT EXISTS`
3. Re-run migration

---

## Validation Checklist

Use this checklist to track your progress:

- [ ] Google Cloud project created
- [ ] Google Calendar API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth credentials created
- [ ] Credentials added to `backend/.env`
- [ ] Supabase migration executed successfully
- [ ] Tables verified in Supabase
- [ ] RLS policies verified
- [ ] Google Calendar connected via OAuth
- [ ] OAuth tokens stored in database
- [ ] Calendar sync triggered successfully
- [ ] At least 50 events ingested
- [ ] Events visible in dashboard
- [ ] Accuracy validation completed
- [ ] Accuracy >= 95% achieved

---

## Success Criteria

Phase 1 is complete when:

✅ **Authentication**: User can register/login and stay authenticated  
✅ **OAuth Setup**: Google Calendar OAuth configured and working  
✅ **Database**: All tables created with proper schema and RLS  
✅ **Ingestion**: Successfully sync 50+ calendar events  
✅ **Accuracy**: 95%+ extraction accuracy for key fields  
✅ **Storage**: All events stored in `raw_tasks` table  
✅ **UI**: Dashboard displays tasks and metrics correctly  

---

## Next Steps After Validation

Once Phase 1 validation is complete:

1. **Document any issues found** - Note edge cases or improvements needed
2. **Optimize extraction logic** - Improve NLP parsing if accuracy is below target
3. **Add error recovery** - Handle edge cases better
4. **Prepare for Phase 2** - Personal Context Encoding Agent

---

## Quick Reference Commands

```bash
# Check backend health
curl http://localhost:8000/api/health

# Test OAuth authorization URL
curl http://localhost:8000/api/auth/google/authorize

# Check Supabase tables (in SQL Editor)
SELECT * FROM raw_tasks LIMIT 10;
SELECT COUNT(*) FROM raw_tasks;

# Check ingestion metrics
curl http://localhost:8000/api/health | jq .metrics
```

---

## Need Help?

If you encounter issues:
1. Check backend logs for detailed error messages
2. Check browser console for frontend errors
3. Verify all environment variables are set correctly
4. Ensure Supabase migration ran successfully
5. Verify Google OAuth credentials are correct

