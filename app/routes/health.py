"""Health check routes for the AI Analysis Service."""

import os
import sys
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config.settings import Settings, get_settings

router = APIRouter()
START_TIME = time.monotonic()


def _scraper_available() -> bool:
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    scraper_root = os.path.join(repo_root, "python-scraper")
    if scraper_root not in sys.path:
        sys.path.insert(0, scraper_root)
    try:
        import scraper_service  # noqa: F401

        return True
    except ImportError:
        return False


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    mongodb: bool
    playwright: str
    scraper: str
    uptime: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """Health check endpoint for the AI Analysis Service."""
    scraper_ready = _scraper_available()
    
    # Check MongoDB URI string (basic validation without blocking)
    mongodb_ok = bool(settings.mongodb_uri and "localhost" not in settings.mongodb_uri)
    
    # Calculate uptime string
    elapsed = time.monotonic() - START_TIME
    uptime_str = f"{int(elapsed // 3600)}h {int((elapsed % 3600) // 60)}m {int(elapsed % 60)}s"

    return {
        "status": "healthy",
        "mongodb": mongodb_ok,
        "playwright": "configured",
        "scraper": "ready" if scraper_ready else "unavailable",
        "uptime": uptime_str,
        "version": settings.app_version,
    }


@router.get("/ready")
@router.get("/readiness")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Readiness check endpoint.
    
    Returns:
        Service readiness status
    """
    return {
        "status": "ready",
        "service": "lead-finder-ai-analysis",
        "version": settings.app_version,
    }


@router.get("/startup")
async def startup_check(settings: Settings = Depends(get_settings)):
    """
    Startup verification endpoint.
    
    Returns:
        Service startup status
    """
    return {
        "status": "started",
        "service": "lead-finder-ai-analysis",
        "version": settings.app_version,
    }


@router.get("/liveness")
async def liveness_check(settings: Settings = Depends(get_settings)):
    """Liveness check endpoint."""
    return {
        "status": "alive",
        "service": "lead-finder-ai-analysis",
    }
