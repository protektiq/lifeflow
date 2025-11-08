# LifeFlow

A multi-agent "cognitive control system" that transforms a user's to-do list into a done list, providing executive-function help and acting as an "ADHD-friendly brain upgrade" by proactively managing their day, predicting blockers, and adapting to their personal context.

## Phase 1: Core Backend & Perception Agent

This phase implements the foundational multi-agent system with focus on robust orchestration, secure authentication, and reliable calendar data ingestion.

## Architecture

- **Backend**: FastAPI (Python) - Core API and agent services
- **Frontend**: Next.js 14+ (TypeScript) - User interface
- **Database**: Supabase (PostgreSQL) - Relational data storage
- **Vector DB**: Chroma - Context embeddings and behavior graph data
- **Orchestration**: LangGraph - Multi-agent workflow management
- **LLM**: OpenAI API - For future Cognition Agent
- **Authentication**: Supabase Auth (Email + Google OAuth)

## Project Structure

```
lifeflow/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── agents/      # Agent implementations
│   │   ├── api/         # API endpoints
│   │   ├── models/      # Data models
│   │   └── utils/       # Utilities
│   └── tests/           # Backend tests
├── frontend/             # Next.js frontend
│   ├── app/             # App Router pages
│   ├── src/
│   │   ├── lib/         # API clients and utilities
│   │   └── types/       # TypeScript types
│   └── middleware.ts    # Route protection
└── supabase/            # Database migrations
    └── migrations/
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+
- Supabase account
- Google Cloud Console project with Calendar API enabled
- OpenAI API key

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your configuration:
```bash
cp .env.example .env
```

5. Run the development server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Copy `.env.local.example` to `.env.local` and fill in your configuration:
```bash
cp .env.local.example .env.local
```

4. Run the development server:
```bash
npm run dev
```

### Supabase Setup

1. Create a Supabase project at [supabase.com](https://supabase.com)

2. Run the database migration:
   - Open Supabase SQL Editor
   - Copy and paste contents of `supabase/migrations/001_initial_schema.sql`
   - Execute the migration

3. Configure authentication providers:
   - Enable Email provider
   - Enable Google OAuth provider
   - Add your Google OAuth credentials

4. See `supabase/README.md` for detailed setup instructions

### Google Calendar API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)

2. Create a new project or select existing one

3. Enable Google Calendar API

4. Create OAuth 2.0 credentials:
   - Go to Credentials > Create Credentials > OAuth 2.0 Client ID
   - Configure OAuth consent screen
   - Add authorized redirect URIs:
     - `http://localhost:8000/api/auth/google/callback` (development)

5. Copy Client ID and Client Secret to your `.env` files

## API Documentation

Once the backend is running:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Phase 1 Milestone

Successfully ingest 50 unique calendar events with 95% accuracy:
- ✅ User authentication (Email + Google OAuth)
- ✅ Google Calendar connection
- ✅ Event ingestion via Perception Agent
- ✅ NLP extraction to RawTask format
- ✅ LangGraph orchestration workflow
- ✅ Data storage in Supabase
- ✅ Basic monitoring and error handling

## Next Steps (Phase 2)

- Personal Context Encoding Agent
- Proactive Planning (Cognition Agent)
- Real-Time Nudging (Action Agent)
- Enhanced UI/UX

## License

MIT

