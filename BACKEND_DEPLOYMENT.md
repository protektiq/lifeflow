# Backend Deployment Guide

This guide covers deploying the LifeFlow FastAPI backend to production.

## Option 1: Railway (Recommended - Easiest)

Railway is the easiest way to deploy FastAPI apps with minimal configuration.

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub

### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Choose your `lifeflow` repository
4. Select the `backend` folder as the root directory

### Step 3: Configure Environment Variables
In Railway dashboard, go to your service → Variables tab, add:

**Required:**
```
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=https://your-backend-url.railway.app/api/auth/google/callback
OPENAI_API_KEY=your_openai_api_key
```

**Optional (with defaults):**
```
CORS_ORIGINS=["https://your-frontend.vercel.app","http://localhost:3000"]
ENVIRONMENT=production
DEBUG=false
CHROMA_MODE=persistent
CHROMA_PERSIST_DIRECTORY=/app/chroma_db
```

### Step 4: Deploy
Railway will automatically:
- Detect Python
- Install dependencies from `requirements.txt`
- Run the start command from `Procfile`

### Step 5: Get Your Backend URL
1. Railway will assign a URL like: `https://your-project.up.railway.app`
2. Copy this URL

### Step 6: Update Frontend Environment Variable
In Vercel dashboard → Settings → Environment Variables, add:
```
NEXT_PUBLIC_API_URL=https://your-project.up.railway.app
```

---

## Option 2: Render

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Create New Web Service
1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: lifeflow-backend
   - **Root Directory**: backend
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Add Environment Variables
Same as Railway (see above)

### Step 4: Deploy
Click "Create Web Service" and Render will deploy automatically.

---

## Option 3: Fly.io

### Step 1: Install Fly CLI
```bash
curl -L https://fly.io/install.sh | sh
```

### Step 2: Login
```bash
fly auth login
```

### Step 3: Initialize Fly App
```bash
cd backend
fly launch
```

### Step 4: Configure
Follow prompts, then edit `fly.toml` if needed.

### Step 5: Set Secrets
```bash
fly secrets set SUPABASE_URL=your_url
fly secrets set SUPABASE_KEY=your_key
# ... etc
```

### Step 6: Deploy
```bash
fly deploy
```

---

## Option 4: Vercel (Serverless Functions)

Vercel can run Python serverless functions, but requires adapting FastAPI.

### Step 1: Create `api/index.py` in backend folder
```python
from app.main import app
from mangum import Mangum

handler = Mangum(app)
```

### Step 2: Create `vercel.json` in backend folder
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
```

### Step 3: Add to requirements.txt
```
mangum==0.17.0
```

### Step 4: Deploy
```bash
cd backend
vercel --prod
```

**Note**: Background tasks (scheduler) won't work on Vercel serverless. Use Railway/Render for full functionality.

---

## Post-Deployment Checklist

1. ✅ Backend URL is accessible: `https://your-backend-url/api/health`
2. ✅ Frontend `NEXT_PUBLIC_API_URL` is set to backend URL
3. ✅ CORS is configured to allow frontend domain
4. ✅ Google OAuth redirect URI matches backend URL
5. ✅ All environment variables are set
6. ✅ Database migrations are run (if needed)

## Testing the Connection

1. Visit your frontend: `https://your-frontend.vercel.app`
2. Open browser DevTools → Network tab
3. Try logging in or making an API call
4. Check that requests go to your backend URL

## Troubleshooting

**CORS Errors:**
- Add frontend URL to `CORS_ORIGINS` in backend environment variables
- Format: `["https://your-frontend.vercel.app"]`

**502 Bad Gateway:**
- Check backend logs for errors
- Verify all environment variables are set
- Check that port is set correctly (`$PORT`)

**Connection Refused:**
- Verify `NEXT_PUBLIC_API_URL` in frontend matches backend URL
- Check backend is actually running and accessible

**Authentication Errors:**
- Verify Supabase credentials are correct
- Check JWT token handling

