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
    service: str
    version: str
    uptime: float
    database: str
    browser: str
    workers: int
    playwright: str
    scraper: str


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """Health check endpoint for the AI Analysis Service."""
    scraper_ready = _scraper_available()
    return {
        "status": "healthy",
        "service": "lead-finder-ai-analysis",
        "version": settings.app_version,
        "uptime": round(time.monotonic() - START_TIME, 3),
        "database": "ready" if settings.mongodb_uri else "not-configured",
        "browser": "disabled" if settings.disable_x11_features else "available",
        "workers": 1,
        "playwright": "installed" if scraper_ready else "unavailable",
        "scraper": "available" if scraper_ready else "unavailable",
    }


@router.get("/ready")
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
