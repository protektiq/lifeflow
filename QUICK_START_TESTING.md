# Quick Start: Testing Email Ingestion

## 🚀 Immediate Next Steps

### 1. Enable Gmail API (5 minutes)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. **APIs & Services** > **Library** > Search "Gmail API" > **Enable**
4. **APIs & Services** > **OAuth consent screen** > Add scope: `https://www.googleapis.com/auth/gmail.readonly`

### 2. Re-authenticate (2 minutes)

**Important:** Users must re-authenticate to grant Gmail permissions.

1. Start backend: `cd backend && python -m uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Log in to LifeFlow
4. Click "Connect Google Calendar" 
5. **Grant both Calendar AND Gmail permissions** ✅

### 3. Test Email Sync (1 minute)

**Option A: Use Frontend**
- Click the sync button in dashboard
- Check tasks list for email tasks (source: "gmail")

**Option B: Use API**
```bash
# Get your JWT token from browser DevTools
TOKEN="your_token_here"

curl -X POST http://localhost:8000/api/ingestion/email/sync \
  -H "Authorization: Bearer $TOKEN"
```

**Option C: Use Python Script**
```bash
# Save as test_email_sync.py (see TESTING_EMAIL_INGESTION.md)
python test_email_sync.py
```

### 4. Verify Results

**Check Database:**
```sql
SELECT source, title, extracted_priority, created_at 
FROM raw_tasks 
WHERE source = 'gmail' 
ORDER BY created_at DESC;
```

**Check Logs:**
Look for:
- ✅ `gmail_messages_fetched` - Emails found
- ✅ `email_extraction_summary` - Tasks extracted
- ✅ `workflow_email_ingestion_start` - Workflow running

## 🧪 Test Scenarios

### Scenario 1: Unread Email with Task
1. Send yourself: "Please review proposal by Friday"
2. Keep it **unread**
3. Run sync
4. ✅ Should create task with due date

### Scenario 2: Flagged Email with Commitment  
1. Send yourself: "I will follow up next week"
2. **Star/Flag** the email
3. Run sync
4. ✅ Should create task with high priority

### Scenario 3: Informational Email
1. Send yourself a newsletter
2. Run sync
3. ✅ Should be skipped (no task created)

## ❌ Troubleshooting

| Problem | Solution |
|---------|----------|
| "No valid credentials" | Re-authenticate with Google OAuth |
| "Gmail API not enabled" | Enable in Google Cloud Console |
| No emails extracted | Check for unread/flagged emails |
| Tasks missing | Check logs for extraction errors |

## 📊 What to Check

- [x] OAuth scopes include Gmail
- [x] User re-authenticated
- [ ] Test emails created
- [ ] Sync completes successfully
- [ ] Email tasks in database (`source='gmail'`)
- [ ] Due dates parsed correctly
- [ ] Priority levels assigned

## 🎯 Success Criteria

✅ Email sync endpoint returns `success: true`  
✅ Email tasks appear in `raw_tasks` table  
✅ Tasks have `source='gmail'`  
✅ Due dates extracted from email bodies  
✅ Non-actionable emails are skipped  

## 📝 Full Testing Guide

See `TESTING_EMAIL_INGESTION.md` for detailed testing instructions.

