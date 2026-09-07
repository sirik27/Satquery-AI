"""
DrishtiAI FastAPI Application — Main entry point.
Mounts all API routers, configures CORS, and initializes services on startup.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.api.routes_analysis import router as analysis_router
from backend.api.routes_ingest import router as ingest_router
from backend.api.routes_temporal import router as temporal_router
from backend.api.routes_chat import router as chat_router
from backend.api.routes_reports import router as reports_router
from backend.database.db import init_db
from backend.services.detector import get_detector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drishti")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle handler."""
    settings = get_settings()
    logger.info("🛰️  DrishtiAI starting up...")
    logger.info(f"   Compute device: {settings.device}")
    logger.info(f"   Dev mode: {settings.dev_mode}")

    # Initialize database
    await init_db()
    logger.info("   Database initialized.")

    # Pre-load YOLO model (downloads weights on first run)
    detector = get_detector()
    logger.info(f"   YOLO model loaded on device: {settings.device}")

    # Ensure data directories exist
    settings.tile_cache_path
    settings.upload_path
    logger.info("   Data directories ready.")

    logger.info("✅ DrishtiAI ready to serve.")
    yield
    logger.info("🛑 DrishtiAI shutting down.")


app = FastAPI(
    title="DrishtiAI — Satellite Intelligence Platform",
    description="Real-time satellite imagery analysis with YOLOv8 detection, "
                "temporal growth analysis, and grounded conversational AI.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(analysis_router, prefix="/api/v1", tags=["Analysis"])
app.include_router(ingest_router, prefix="/api/v1", tags=["Ingest"])
app.include_router(temporal_router, prefix="/api/v1", tags=["Temporal"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat"])
app.include_router(reports_router, prefix="/api/v1", tags=["Reports"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DrishtiAI",
        "device": settings.device,
        "dev_mode": settings.dev_mode,
    }
