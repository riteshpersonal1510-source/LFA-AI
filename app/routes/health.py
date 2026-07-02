"""Health check routes for the AI Analysis Service."""

import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config.settings import Settings, get_settings

router = APIRouter()
START_TIME = time.monotonic()


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


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """Health check endpoint for the AI Analysis Service."""
    return {
        "status": "healthy",
        "service": "lead-finder-ai-analysis",
        "version": settings.app_version,
        "uptime": round(time.monotonic() - START_TIME, 3),
        "database": "ready" if settings.mongodb_uri else "not-configured",
        "browser": "available",
        "workers": 1,
        "playwright": "installed",
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
