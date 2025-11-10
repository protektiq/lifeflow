# Testing Email Ingestion - Step-by-Step Guide

## Prerequisites

### 1. Enable Gmail API in Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Navigate to **APIs & Services** > **Library**
4. Search for "Gmail API"
5. Click **Enable**

### 2. Update OAuth Consent Screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Ensure scopes include:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/gmail.readonly`
3. Add both scopes to your OAuth consent screen

### 3. Verify Environment Variables

Ensure your `.env` file has:
```bash
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

## Testing Steps

### Step 1: Re-authenticate with New Scopes

Since we added Gmail scopes, users need to re-authenticate:

1. **Start your backend server:**
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload
   ```

2. **Start your frontend:**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Reconnect Google Account:**
   - Log into your LifeFlow account
   - Go to Dashboard
   - Click "Connect Google Calendar" (or similar)
   - You should see a consent screen asking for **both Calendar and Gmail** permissions
   - Grant permissions

### Step 2: Prepare Test Emails

Create test emails in your Gmail account:

1. **Create an unread email with a task:**
   - Send yourself an email with subject: "Review project proposal"
   - Body: "Please review the proposal by Friday, December 15th"
   - Keep it **unread**

2. **Create a flagged email with a commitment:**
   - Send yourself an email with subject: "Follow up on meeting"
   - Body: "I will follow up with the client next week. Due by Monday."
   - **Star/Flag** the email

3. **Create an email without actionable tasks:**
   - Send yourself a newsletter or informational email
   - This should be skipped during extraction

### Step 3: Test Email Sync via API

#### Option A: Using curl

```bash
# Get your auth token (from browser dev tools or login response)
TOKEN="your_jwt_token_here"

# Test email sync endpoint
curl -X POST http://localhost:8000/api/ingestion/email/sync \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

#### Option B: Using Python requests

```python
import requests

# Your JWT token
token = "your_jwt_token_here"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Test email sync
response = requests.post(
    "http://localhost:8000/api/ingestion/email/sync",
    headers=headers
)

print(response.json())
```

#### Option C: Using the frontend

If you have a sync button in the UI, clicking it should now trigger both calendar and email ingestion.

### Step 4: Verify Results

#### Check Database

Query the `raw_tasks` table to see extracted email tasks:

```sql
-- In Supabase SQL Editor
SELECT 
    id,
    source,
    title,
    description,
    start_time,
    end_time,
    extracted_priority,
    is_critical,
    is_urgent,
    created_at
FROM raw_tasks
WHERE source = 'gmail'
ORDER BY created_at DESC;
```

**Expected results:**
- Tasks from emails with `source = 'gmail'`
- Titles extracted from email subjects or ChatGPT analysis
- Due dates parsed from email bodies
- Priority levels assigned based on flags and content

#### Check Logs

Monitor backend logs for:
- `gmail_messages_listed` - Shows emails found
- `gmail_messages_fetched` - Shows emails processed
- `chatgpt_email_extraction_start` - Shows NLP extraction
- `email_extraction_summary` - Shows extraction results
- `workflow_email_ingestion_start` - Shows workflow progress

### Step 5: Test Edge Cases

1. **No unread/flagged emails:**
   - Mark all emails as read
   - Run sync - should complete without errors

2. **Email with no actionable tasks:**
   - Send informational email
   - Run sync - should skip it (check logs)

3. **Email with complex date formats:**
   - Test emails with "due next week", "by EOD Friday", etc.
   - Verify dates are parsed correctly

## Troubleshooting

### Issue: "No valid credentials found"

**Solution:**
- Re-authenticate with Google OAuth
- Ensure Gmail API is enabled in Google Cloud Console
- Check that OAuth tokens are stored in `oauth_tokens` table

### Issue: "Gmail API not enabled"

**Solution:**
- Enable Gmail API in Google Cloud Console
- Wait a few minutes for changes to propagate

### Issue: "Insufficient permissions"

**Solution:**
- Check OAuth consent screen includes Gmail scope
- Re-authenticate to grant new permissions
- Verify scopes in `oauth_tokens.scope` field

### Issue: No emails extracted

**Possible causes:**
- No unread/flagged emails
- ChatGPT extraction marked emails as non-actionable
- Check logs for `email_extraction_summary` to see skipped count

### Issue: Rate limiting

**Solution:**
- Gmail API has rate limits (250 quota units per user per second)
- If hitting limits, reduce `max_results` in `fetch_gmail_messages()`
- Add exponential backoff for retries

## Verification Checklist

- [ ] Gmail API enabled in Google Cloud Console
- [ ] OAuth consent screen includes Gmail scope
- [ ] User re-authenticated with new scopes
- [ ] Test emails created (unread/flagged)
- [ ] Email sync endpoint returns success
- [ ] Email tasks appear in `raw_tasks` table with `source='gmail'`
- [ ] Due dates extracted correctly
- [ ] Priority levels assigned appropriately
- [ ] Non-actionable emails are skipped
- [ ] Logs show proper workflow execution

## Quick Start Testing Script

Create a simple test script to verify everything works:

```python
# test_email_sync.py
import requests
import os
from datetime import datetime

# Get token from your browser (DevTools > Application > Local Storage > supabase.auth.token)
TOKEN = os.getenv("LIFEFLOW_TOKEN", "your_token_here")
API_URL = "http://localhost:8000"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

print("Testing Email Sync...")
print("=" * 50)

# Test email sync
response = requests.post(
    f"{API_URL}/api/ingestion/email/sync",
    headers=headers
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
print()

# Get raw tasks
response = requests.get(
    f"{API_URL}/api/tasks/raw",
    headers=headers
)

tasks = response.json()
email_tasks = [t for t in tasks if t.get("source") == "gmail"]

print(f"Total tasks: {len(tasks)}")
print(f"Email tasks: {len(email_tasks)}")
print()

if email_tasks:
    print("Sample email tasks:")
    for task in email_tasks[:5]:
        print(f"  - {task.get('title')} (Priority: {task.get('extracted_priority')})")
else:
    print("No email tasks found. Check:")
    print("  1. Do you have unread/flagged emails?")
    print("  2. Did you re-authenticate with Gmail scope?")
    print("  3. Check backend logs for errors")
```

Run it:
```bash
export LIFEFLOW_TOKEN="your_token_here"
python test_email_sync.py
```

## Next Steps

### 1. Frontend Integration (Optional Enhancement)

The frontend already works! The existing sync button will now sync both calendar and emails. Optional enhancements:

- Show source indicator (Calendar vs Gmail) in task list
- Add separate email sync button/indicator
- Display email metadata (sender, date) in task details

### 2. Error Handling

Consider adding:
- User-friendly error messages for Gmail API failures
- Retry logic for transient failures
- Notification when email sync completes

### 3. Performance Optimization

- Batch email processing
- Cache email metadata to avoid re-processing
- Incremental sync (only new emails)

### 4. Testing in Production

- Test with real email volumes
- Monitor API quota usage
- Set up alerts for failures

### 5. User Experience

- Add email sync status indicator
- Show last sync time
- Allow users to configure email filters

## API Endpoints Reference

### Email Sync
```http
POST /api/ingestion/email/sync
Authorization: Bearer <token>
```

### Calendar Sync (now includes emails)
```http
POST /api/ingestion/calendar/sync
Authorization: Bearer <token>
```

### Get Raw Tasks (includes email tasks)
```http
GET /api/tasks/raw?start_date=2024-01-01&end_date=2024-12-31
Authorization: Bearer <token>
```

## Monitoring

Watch for these metrics:
- Email ingestion success rate
- Average emails processed per sync
- ChatGPT extraction accuracy
- Task extraction rate (tasks/emails)
- API quota usage

