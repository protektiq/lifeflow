# Google OAuth Setup Guide - Fixing "invalid_client" Error

## Problem
You're getting "Error 401: invalid_client - The OAuth client was not found" because your `.env` file contains placeholder values instead of real Google OAuth credentials.

## Solution: Get Your Real Google OAuth Credentials

### Step 1: Go to Google Cloud Console
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. Select your project (or create a new one if needed)

### Step 2: Enable Google Calendar API
1. Go to **APIs & Services** > **Library**
2. Search for "Google Calendar API"
3. Click on it and click **Enable**

### Step 3: Configure OAuth Consent Screen
1. Go to **APIs & Services** > **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace account)
3. Fill in the required information:
   - App name: LifeFlow (or your app name)
   - User support email: Your email
   - Developer contact information: Your email
4. Click **Save and Continue**
5. Add scopes:
   - Click **Add or Remove Scopes**
   - Search for and add: `https://www.googleapis.com/auth/calendar.readonly`
   - Click **Update** then **Save and Continue**
6. Add test users (if app is in testing mode):
   - Add your email address as a test user
   - Click **Save and Continue**
7. Review and go back to dashboard

### Step 4: Create OAuth 2.0 Credentials
1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth 2.0 Client ID**
3. If prompted, configure the OAuth consent screen (see Step 3)
4. Choose **Web application** as the application type
5. Give it a name (e.g., "LifeFlow Calendar Integration")
6. **Authorized redirect URIs** - Add this EXACT URL:
   ```
   http://localhost:8000/api/auth/google/callback
   ```
   ⚠️ **IMPORTANT**: The URL must match EXACTLY (including http vs https, port number, and path)
7. Click **Create**
8. **Copy the credentials**:
   - **Client ID**: Something like `123456789-abc123def456.apps.googleusercontent.com`
   - **Client Secret**: Something like `GOCSPX-abc123def456xyz789`

### Step 5: Update Your .env File
1. Open `backend/.env` file
2. Replace the placeholder values with your real credentials:

```bash
GOOGLE_CLIENT_ID=your-actual-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-actual-client-secret-here
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

3. **Important**: 
   - No spaces around the `=` sign
   - No quotes around the values
   - Make sure there are no trailing spaces
   - The redirect URI must match EXACTLY what you entered in Google Cloud Console

### Step 6: Restart Your Backend Server
After updating the `.env` file:
```bash
cd backend
# Stop your current server (Ctrl+C)
# Then restart it
python -m uvicorn app.main:app --reload
```

### Step 7: Test the Connection
1. Go to your dashboard
2. Click "Connect Google Calendar"
3. You should be redirected to Google's authorization page
4. Sign in and grant permissions
5. You should be redirected back to your dashboard

## Troubleshooting

### Still getting "invalid_client"?
1. **Double-check the Client ID format**: Should end with `.apps.googleusercontent.com`
2. **Verify Client Secret**: Should start with `GOCSPX-`
3. **Check redirect URI**: Must match EXACTLY in both `.env` and Google Cloud Console
4. **Restart backend**: Environment variables are loaded at startup
5. **Check for typos**: No extra spaces, quotes, or special characters

### "Redirect URI mismatch" error?
- The redirect URI in your `.env` must match EXACTLY what's in Google Cloud Console
- Check for:
  - `http` vs `https`
  - Port number (`8000`)
  - Path (`/api/auth/google/callback`)
  - Trailing slashes

### OAuth client not found?
- Make sure you're using the correct Google Cloud project
- Verify the OAuth client wasn't deleted
- Check that you copied the entire Client ID and Secret (no truncation)

## Security Notes
- ⚠️ Never commit your `.env` file to git (it's already in `.gitignore`)
- ⚠️ Keep your Client Secret secure
- ⚠️ Use different credentials for development and production
- ⚠️ Rotate credentials if they're accidentally exposed

## Need Help?
If you're still having issues:
1. Run the diagnostic script: `python3 backend/scripts/check_google_oauth.py`
2. Check backend logs for detailed error messages
3. Verify your Google Cloud project settings

