"""Routes package for the AI Analysis Service."""

from fastapi import APIRouter
from .health import router as health_router
from .analysis import router as analysis_router
from ..services.whatsapp.api import router as legacy_whatsapp_router
from .whatsapp import router as new_whatsapp_router

whatsapp_router = APIRouter()
whatsapp_router.include_router(legacy_whatsapp_router)
whatsapp_router.include_router(new_whatsapp_router)

__all__ = ["health_router", "analysis_router", "whatsapp_router"]
