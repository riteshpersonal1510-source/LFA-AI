"""Routes package for the AI Analysis Service."""

from .health import router as health_router
from .analysis import router as analysis_router
from .whatsapp import router as whatsapp_router

__all__ = ["health_router", "analysis_router", "whatsapp_router"]
