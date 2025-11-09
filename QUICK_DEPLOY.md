# Quick Deployment Guide

## Backend Deployment (Railway - Recommended)

### Step 1: Deploy Backend
1. Go to [railway.app](https://railway.app) and sign up
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your `lifeflow` repository
4. **Important**: Set root directory to `backend` folder
5. Railway will auto-detect Python and install dependencies

### Step 2: Add Environment Variables
In Railway dashboard → Variables tab, add:

```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-backend-url.railway.app/api/auth/google/callback
OPENAI_API_KEY=your_openai_key
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:3000"]
ENVIRONMENT=production
DEBUG=false
```

**Note**: Replace `your-backend-url.railway.app` with your actual Railway URL after first deployment.

### Step 3: Get Backend URL
After deployment, Railway will show your URL like: `https://lifeflow-production.up.railway.app`

---

## Frontend Configuration

### Step 1: Add Backend URL to Vercel
1. Go to [vercel.com](https://vercel.com) → Your project → Settings → Environment Variables
2. Add:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-url.railway.app
   ```
3. Redeploy (or wait for next commit)

---

## Testing

1. **Backend Health Check**: Visit `https://your-backend-url.railway.app/api/health`
   - Should return: `{"status": "healthy", ...}`

2. **Frontend**: Visit your Vercel URL
   - Open browser DevTools → Network tab
   - Try logging in or making an API call
   - Check that requests go to your backend URL

---

## Troubleshooting

**CORS Errors:**
- Make sure `CORS_ORIGINS` includes your frontend URL
- Format: `["https://your-frontend.vercel.app"]` (JSON array)

**502 Bad Gateway:**
- Check Railway logs for errors
- Verify all environment variables are set
- Check backend health endpoint

**Connection Refused:**
- Verify `NEXT_PUBLIC_API_URL` matches backend URL exactly
- Check backend is running (visit health endpoint)

---

## Alternative: Render.com

If Railway doesn't work, try Render:
1. Go to [render.com](https://render.com)
2. New Web Service → Connect GitHub repo
3. Root Directory: `backend`
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add same environment variables as above

