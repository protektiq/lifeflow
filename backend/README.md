# LifeFlow Backend

FastAPI backend for the LifeFlow multi-agent cognitive control system. This backend provides RESTful APIs for task management, calendar integration, AI-powered planning, and notification services.

## 🏗️ Architecture

The backend is built using:
- **FastAPI** - Modern, fast web framework for building APIs
- **Python 3.11+** - Programming language
- **Supabase** - PostgreSQL database and authentication
- **Chroma** - Vector database for context embeddings
- **LangGraph** - Multi-agent workflow orchestration
- **OpenAI API** - AI-powered task extraction and planning
- **APScheduler** - Background task scheduling for notifications
- **Google Calendar API** - Calendar event ingestion

## 📁 Project Structure

```
backend/
├── app/
│   ├── agents/              # AI agent implementations
│   │   ├── action/         # Action agents (nudger, notification sender)
│   │   ├── cognition/      # Cognition agents (encoding, planner, learning)
│   │   ├── orchestration/  # LangGraph workflows
│   │   └── perception/     # Perception agents (ingestion, NLP extraction)
│   ├── api/                # REST API endpoints
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── ingestion.py    # Calendar sync endpoints
│   │   ├── tasks.py        # Task management endpoints
│   │   ├── energy_level.py # Energy level tracking endpoints
│   │   ├── plans.py        # Daily plan generation endpoints
│   │   ├── feedback.py     # User feedback endpoints
│   │   ├── notifications.py # Notification management endpoints
│   │   ├── reminders.py    # Reminder endpoints
│   │   └── task_manager.py # Task manager sync endpoints (Todoist, etc.)
│   ├── models/             # Pydantic data models
│   ├── services/           # Business logic services
│   ├── utils/              # Utilities and helpers
│   │   ├── scheduler.py   # Background scheduler for notifications
│   │   └── monitoring.py  # Metrics and logging
│   ├── config.py           # Configuration management
│   ├── database.py         # Database connection
│   └── main.py             # FastAPI application entry point
├── tests/                  # Backend tests
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🚀 Setup

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   
   Create a `.env` file in the backend directory with the following variables:
   ```bash
   # Supabase Configuration
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   
   # Google OAuth
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   
   # OpenAI API
   OPENAI_API_KEY=your_openai_api_key
   
   # Chroma Vector Database
   CHROMA_HOST=localhost
   CHROMA_PORT=8000
   
   # Email Configuration (for notifications)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your_email@gmail.com
   SMTP_PASSWORD=your_app_password
   SMTP_FROM_EMAIL=your_email@gmail.com
   
   # CORS Configuration
   CORS_ORIGINS=http://localhost:3000,http://localhost:3001
   
   # Application Settings
   ENVIRONMENT=development
   LOG_LEVEL=INFO
   ```

   > 💡 See [ENV_SETUP.md](../ENV_SETUP.md) for detailed instructions on obtaining these credentials.

5. **Run database migrations:**
   
   Ensure all Supabase migrations have been run. See [supabase/README.md](../supabase/README.md) for details.

6. **Start the development server:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

   The backend will be available at `http://localhost:8000`

## 📚 API Documentation

Once the server is running, you can access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## 🔌 API Endpoints

### Authentication (`/api/auth`)
- `POST /api/auth/login` - User login with email/password
- `GET /api/auth/google` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - Google OAuth callback handler

### Calendar Ingestion (`/api/ingestion`)
- `POST /api/ingestion/calendar/sync` - Sync calendar events and extract tasks

### Tasks (`/api/tasks`)
- `GET /api/tasks` - Get all tasks for the authenticated user
- `GET /api/tasks/{task_id}` - Get a specific task
- `PUT /api/tasks/{task_id}` - Update task (flags, status, etc.)
- `DELETE /api/tasks/{task_id}` - Delete a task

### Energy Levels (`/api/energy-level`)
- `POST /api/energy-level` - Set energy level for a date
- `GET /api/energy-level/{date}` - Get energy level for a date
- `GET /api/energy-level/history` - Get energy level history

### Daily Plans (`/api/plans`)
- `POST /api/plans/generate` - Generate a daily plan for a date
- `GET /api/plans/{date}` - Get daily plan for a date
- `GET /api/plans/history` - Get plan history

### Feedback (`/api/feedback`)
- `POST /api/feedback` - Submit feedback on tasks (done, snooze, etc.)

### Notifications (`/api/notifications`)
- `GET /api/notifications` - Get all notifications for the user
- `PUT /api/notifications/{notification_id}/dismiss` - Dismiss a notification
- `GET /api/notifications/unread` - Get unread notification count

### Reminders (`/api/reminders`)
- `GET /api/reminders` - Get all reminders for the user
- `GET /api/reminders/{date}` - Get reminders for a specific date

### Task Manager Sync (`/api/task-manager`)
- `POST /api/task-manager/todoist/sync` - Sync with Todoist
- `POST /api/task-manager/todoist/connect` - Connect Todoist account
- `POST /api/task-manager/conflicts/resolve` - Resolve sync conflicts

## 🤖 Agents & Workflows

### Orchestration Agents

The backend uses LangGraph for orchestrating multi-agent workflows:

1. **Calendar Ingestion Workflow** (`app/agents/orchestration/workflow.py`)
   - Verifies OAuth credentials
   - Fetches events from Google Calendar
   - Extracts tasks using NLP
   - Stores tasks in database
   - Generates context embeddings

2. **Planning Workflow** (`app/agents/cognition/planner.py`)
   - Fetches user tasks and energy levels
   - Generates personalized daily plans using OpenAI
   - Stores plans in database

### Action Agents

- **Nudger Agent** (`app/agents/action/nudger.py`)
  - Monitors scheduled tasks
  - Creates notifications when tasks are due
  - Sends email reminders (if configured)

### Perception Agents

- **Ingestion Agent** (`app/agents/perception/ingestion.py`)
  - Fetches calendar events from Google Calendar API

- **Extraction Agent** (`app/agents/perception/extraction.py`)
  - Uses OpenAI to extract tasks from calendar events
  - Identifies deadlines, priorities, and actionable items

### Cognition Agents

- **Encoding Agent** (`app/agents/cognition/encoding.py`)
  - Generates context embeddings for tasks
  - Stores embeddings in Chroma vector database

- **Planner Agent** (`app/agents/cognition/planner.py`)
  - Generates personalized daily plans
  - Considers energy levels, priorities, and task history

## ⏰ Background Scheduler

The backend includes a background scheduler (APScheduler) that:

- Runs every 2 minutes
- Checks for tasks due in the next 5 minutes
- Triggers the Action Agent (Nudger) to create notifications
- Sends email reminders (if SMTP is configured)

The scheduler starts automatically when the FastAPI application starts and shuts down gracefully on application termination.

## 🧪 Testing

Run tests using pytest:

```bash
cd backend
pytest
```

Run tests with coverage:

```bash
pytest --cov=app --cov-report=html
```

## 📊 Monitoring & Logging

The backend includes structured logging and metrics:

- **Structured Logging**: All events are logged with context
- **Ingestion Metrics**: Track sync success rates and statistics
- **Health Check**: Monitor application health via `/api/health`

## 🔒 Security

- **JWT Authentication**: All endpoints (except auth) require JWT tokens
- **CORS**: Configured to allow requests from frontend origins
- **Environment Variables**: Sensitive data stored in environment variables
- **OAuth 2.0**: Secure Google Calendar integration

## 🚢 Deployment

See [BACKEND_DEPLOYMENT.md](../BACKEND_DEPLOYMENT.md) for deployment instructions.

For quick deployment, see [QUICK_DEPLOY.md](../QUICK_DEPLOY.md).

## 📝 Dependencies

Key dependencies (see `requirements.txt` for full list):

- `fastapi==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `supabase==2.0.0` - Database client
- `langgraph==0.0.20` - Workflow orchestration
- `openai==1.3.0` - AI API client
- `chromadb==0.4.18` - Vector database
- `google-api-python-client==2.108.0` - Google Calendar API
- `apscheduler==3.10.4` - Background scheduler
- `pydantic==2.5.0` - Data validation

## 🐛 Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **Database connection errors**: Verify Supabase credentials in `.env`
3. **OAuth errors**: Check Google OAuth credentials and redirect URIs
4. **Chroma connection errors**: Ensure Chroma server is running (if using remote instance)

## 📚 Additional Resources

- [Main README](../README.md) - Project overview
- [Environment Setup Guide](../ENV_SETUP.md) - Detailed setup instructions
- [Running Guide](../RUNNING.md) - How to run the application
- [Phase 3 Notifications](../PHASE3_NOTIFICATIONS.md) - Notification system docs

---

**Made with ❤️ for LifeFlow**
