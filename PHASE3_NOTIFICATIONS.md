# Phase 3: Notification System Documentation

## Overview

The notification system provides real-time delivery of micro-nudges when scheduled tasks are due. It includes:
- **In-app notifications** displayed in the dashboard
- **Email notifications** sent to users' email addresses
- **Automatic scheduling** via background scheduler

## How It Works

### When Notifications Are Sent

1. **Scheduler Frequency**: Every 2 minutes, the system checks for tasks due to start
2. **Time Window**: Tasks with `predicted_start` within the next 5 minutes trigger notifications
3. **One-Time Only**: Each task receives only one notification (duplicates are prevented)

### Notification Flow

```
Scheduler (every 2 min) 
  → Action Agent checks daily_plans
  → Finds tasks due in next 5 minutes
  → Creates notification record
  → Sends notification (in-app + email)
  → Marks notification as "sent"
```

## Configuration

### Email Configuration

Add these environment variables to `backend/.env`:

```bash
# Email Settings
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=LifeFlow <your-email@gmail.com>
```

**For Gmail:**
1. Enable 2-factor authentication
2. Generate an "App Password" (not your regular password)
3. Use the app password in `SMTP_PASSWORD`

**For Other Providers:**
- **SendGrid**: `SMTP_HOST=smtp.sendgrid.net`, `SMTP_PORT=587`
- **Mailgun**: `SMTP_HOST=smtp.mailgun.org`, `SMTP_PORT=587`
- **Custom SMTP**: Use your provider's SMTP settings

### Database Migration

Run the migration to enable email lookup:

```sql
-- Run in Supabase SQL Editor
-- File: supabase/migrations/004_get_user_email_function.sql
```

This creates a function to retrieve user emails from `auth.users`.

## API Endpoints

### Get Notifications
```
GET /api/notifications
Query params:
  - status: optional (pending, sent, dismissed)
  - limit: optional (default: 50)
```

### Get Pending Notifications
```
GET /api/notifications/pending
Query params:
  - limit: optional (default: 50)
```

### Dismiss Notification
```
POST /api/notifications/{notification_id}/dismiss
```

### Get Single Notification
```
GET /api/notifications/{notification_id}
```

## Frontend Usage

The `NotificationCenter` component is automatically included in the dashboard and:
- Auto-refreshes every 30 seconds
- Shows pending notifications prominently
- Allows dismissing notifications
- Displays notification status and timing

## Notification Types

### Micro-Nudges
- **Trigger**: Task's scheduled start time arrives
- **Message Format**: 
  - Critical: `🔴 CRITICAL: {task_title} is starting now`
  - Urgent: `⚠️ URGENT: {task_title} is starting now`
  - Normal: `📋 {task_title} is starting now`

## Email Templates

Emails include:
- **Subject**: Same as notification message
- **HTML Body**: Formatted with priority badges and styling
- **Text Body**: Plain text fallback

## Monitoring

All notification events are logged:
- `nudge_sent` - Notification sent successfully
- `email_nudge_sent` - Email notification sent
- `nudger_check_start` - Scheduler check started
- `nudger_check_complete` - Scheduler check completed
- `email_sent` - Email delivery successful
- `email_disabled` - Email disabled in config

## Troubleshooting

### Email Not Sending

1. **Check Configuration**:
   ```bash
   # Verify EMAIL_ENABLED=true in .env
   # Verify SMTP credentials are correct
   ```

2. **Check Logs**:
   - Look for `email_sent` or `email_disabled` events
   - Check for SMTP authentication errors

3. **Test SMTP Connection**:
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   ```

### Notifications Not Appearing

1. **Check Scheduler**: Verify scheduler is running (check logs for `scheduler_initialized`)
2. **Check Tasks**: Ensure tasks have `predicted_start` times set
3. **Check Time Window**: Tasks must be within 5 minutes of current time
4. **Check Database**: Verify notifications are being created in `notifications` table

### User Email Not Found

1. **Run Migration**: Ensure `004_get_user_email_function.sql` is executed
2. **Check User**: Verify user exists in `auth.users` table
3. **Check Logs**: Look for `email_user_lookup` errors

## Testing

### Manual Test

1. Create a daily plan with a task scheduled 3 minutes from now
2. Wait 2 minutes for scheduler to run
3. Check:
   - Notification appears in dashboard
   - Email is sent (if configured)
   - Notification status is "sent"

### Automated Test

Run integration tests:
```bash
cd backend
pytest tests/integration/test_phase3_loop.py -v
```

## Security Notes

- Email credentials should be stored securely in `.env` (never commit to git)
- Use app-specific passwords, not account passwords
- Email service gracefully degrades if email fails (in-app notifications still work)
- User email lookup uses SECURITY DEFINER function for proper access control

