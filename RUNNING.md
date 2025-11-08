# Running LifeFlow Application

## Prerequisites

1. ✅ Backend dependencies installed (in virtual environment)
2. ✅ Frontend dependencies installed (`npm install`)
3. ✅ Environment variables configured (`.env` and `.env.local`)

## Running the Backend (Port 8000)

### Step 1: Navigate to backend directory
```bash
cd /home/carlos/lifeflow/backend
```

### Step 2: Activate virtual environment
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### Step 3: Run the FastAPI server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What this does:**
- `--reload` - Auto-reloads when code changes (development mode)
- `--host 0.0.0.0` - Makes server accessible from all network interfaces
- `--port 8000` - Runs on port 8000

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### Verify Backend is Running

Open in browser or use curl:
- API Root: http://localhost:8000/
- Health Check: http://localhost:8000/api/health
- API Docs: http://localhost:8000/docs (Swagger UI)
- ReDoc: http://localhost:8000/redoc

## Running the Frontend (Port 3000)

### Step 1: Open a NEW terminal window/tab
(Keep the backend running in the first terminal)

### Step 2: Navigate to frontend directory
```bash
cd /home/carlos/lifeflow/frontend
```

### Step 3: Run the Next.js development server
```bash
npm run dev
```

**Expected output:**
```
  ▲ Next.js 16.0.1
  - Local:        http://localhost:3000
  - Network:      http://192.168.x.x:3000

 ✓ Ready in 2.5s
```

### Verify Frontend is Running

Open in browser:
- Frontend: http://localhost:3000

## Running Both Servers Together

You need **two terminal windows/tabs**:

**Terminal 1 (Backend):**
```bash
cd /home/carlos/lifeflow/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd /home/carlos/lifeflow/frontend
npm run dev
```

## Quick Start Scripts (Optional)

You can create helper scripts to make this easier:

### Backend start script (`backend/start.sh`):
```bash
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Make it executable:
```bash
chmod +x backend/start.sh
```

Then run:
```bash
./backend/start.sh
```

## Stopping the Servers

- **Backend**: Press `CTRL+C` in the backend terminal
- **Frontend**: Press `CTRL+C` in the frontend terminal
- **Deactivate venv**: Type `deactivate` after stopping backend

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Find what's using port 8000
lsof -i :8000
# Kill the process or use a different port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

**Module not found errors:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Environment variable errors:**
- Check `.env` file exists in `backend/` directory
- Verify all required variables are set

### Frontend Issues

**Port 3000 already in use:**
```bash
# Use a different port
npm run dev -- -p 3001
```

**Module not found errors:**
- Reinstall dependencies: `npm install`

**API connection errors:**
- Verify backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local` matches backend URL

## Development Workflow

1. Start backend first (Terminal 1)
2. Start frontend second (Terminal 2)
3. Make code changes - both servers auto-reload
4. Test in browser at http://localhost:3000
5. Check backend logs in Terminal 1 for API calls
6. Check frontend logs in Terminal 2 for build/rendering info

## Production Deployment

For production, you'll want to:
- Remove `--reload` flag
- Use a production WSGI server (like Gunicorn)
- Build frontend: `npm run build`
- Serve frontend with `npm start` or a static file server

