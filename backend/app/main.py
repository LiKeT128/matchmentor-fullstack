"""FastAPI application entry point."""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback

from app.config import get_settings
from app.database import engine, Base
from app.models import User, Match, Coach, Payment, Booking, Review, Availability  # Ensure all models are loaded
from app.api import auth_router, matches_router, coaches_router, payments_router, bookings_router, sessions_router, compat_router, demo_router, debug_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Creates database tables on startup.
    """
    logger.info("Starting MatchMentor API...")
    
    # Debug DB connection (sanitized)
    from sqlalchemy.engine import make_url
    try:
        url = make_url(settings.database_url)
        logger.info(f"Connecting to database at {url.host}:{url.port}")
    except Exception:
        logger.error("Could not parse DATABASE_URL")

    # Debug: Inspect DB Schema
    from sqlalchemy import inspect
    try:
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        logger.info(f"DEBUG: users table columns: {[c['name'] for c in columns]}")
    except Exception as e:
        logger.error(f"DEBUG: Could not inspect users table: {e}")


    # Load OpenDota hero cache FIRST (before any match processing)
    try:
        from app.services.opendota_client import OpenDotaClient
        hero_count = await OpenDotaClient.load_heroes()
        logger.info(f"✓ OpenDota hero cache loaded: {hero_count} heroes")
    except Exception as e:
        logger.error(f"Failed to load OpenDota hero cache: {e}")
        # Non-fatal: will use fallback hero_mapping.py

    # Run Alembic migrations
    try:
        from alembic.config import Config
        from alembic import command
        
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations complete")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # Fallback: try to create tables if they don't exist (won't fix missing columns though)
        if not os.getenv("DB_SKIP_CREATE"):
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified/created via SQLAlchemy")
    
    yield
    
    logger.info("Shutting down MatchMentor API...")


# Create FastAPI application
app = FastAPI(
    title="MatchMentor API",
    description="Dota 2 replay analyzer with coaching marketplace",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
origins = [
    settings.frontend_url,
    "https://matchmentor-frontend.vercel.app",  # Explicitly allow production frontend
    "http://localhost:3000",
    "http://localhost:5173",
]

# Ensure frontend_url doesn't have a trailing slash for CORS
if settings.frontend_url.endswith("/"):
    origins.append(settings.frontend_url[:-1])

logger.info(f"CORS origins configured: {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GLOBAL EXCEPTION HANDLER MIDDLEWARE for debugging
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"!!! CRITICAL UNHANDLED EXCEPTION ON {request.url} !!!")
        traceback.print_exc()  # Ensures output to Railway logs (stdout)
        logger.error(f"Unhandled exception: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(e)}", "trace": traceback.format_exc()}
        )

# Include routers
app.include_router(auth_router)
app.include_router(matches_router)
app.include_router(coaches_router)
app.include_router(payments_router)
app.include_router(bookings_router)
app.include_router(sessions_router)
app.include_router(compat_router)
app.include_router(demo_router)
app.include_router(debug_router)


@app.get("/")
async def root() -> dict:
    """Root endpoint with API info."""
    return {
        "name": "MatchMentor API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health() -> dict:
    """
    Health check endpoint.
    
    Returns:
        Status dict for load balancer checks.
    """
    return {
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api/stats")
async def stats() -> dict:
    """
    Public API stats endpoint.
    
    Returns:
        Basic platform statistics.
    """
    # In production, these would come from database
    return {
        "total_matches_analyzed": 0,
        "total_users": 0,
        "total_coaches": 0
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=settings.debug
    )
