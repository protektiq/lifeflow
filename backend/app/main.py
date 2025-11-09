"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import auth, ingestion, tasks, energy_level, plans, feedback, notifications
from app.utils.monitoring import ingestion_metrics
from app.utils.scheduler import start_scheduler, shutdown_scheduler
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="LifeFlow API",
    description="Multi-agent cognitive control system for task management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(energy_level.router, prefix="/api/energy-level", tags=["energy-level"])
app.include_router(plans.router, prefix="/api/plans", tags=["plans"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "LifeFlow API",
        "metrics": ingestion_metrics.get_metrics(),
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "LifeFlow API", "version": "1.0.0"}

