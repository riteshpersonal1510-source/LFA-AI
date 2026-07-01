"""Health check routes for the AI Analysis Service."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config.settings import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str
    uptime: float


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint for the AI Analysis Service.
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "lead-finder-ai-analysis",
        "version": settings.app_version,
        "uptime": 0.0,  # In production, track actual uptime
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
