#!/usr/bin/env python3
"""
Main entry point for the AI Analysis Service.

This module starts the FastAPI server and handles graceful shutdown.
"""

import asyncio
import logging
import os
import signal
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.core.exception_handlers import (
    AnalysisException,
    register_exception_handlers,
)
from app.core.middleware import register_middleware
from app.routes import health_router, analysis_router, whatsapp_router
from app.services.whatsapp.api import router as whatsapp_api_router
from app.services.whatsapp.database import connect as db_connect, disconnect as db_disconnect

# ---------------------------------------------------------------------------
# Mount local or sibling python-scraper package for unified deployment
# ---------------------------------------------------------------------------
_AI_SERVICE_ROOT = os.path.dirname(os.path.abspath(__file__))
_APP_ROOT = os.path.join(_AI_SERVICE_ROOT, "app")
_REPO_ROOT = os.path.dirname(_AI_SERVICE_ROOT)
_PYTHON_SCRAPER_ROOT = os.path.join(_REPO_ROOT, "python-scraper")

# Prioritize the internal app/scraper_service package if present
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

if os.path.isdir(_PYTHON_SCRAPER_ROOT) and _PYTHON_SCRAPER_ROOT not in sys.path:
    sys.path.insert(0, _PYTHON_SCRAPER_ROOT)


SCRAPER_AVAILABLE = False
scrape_router = None
browser_pool = None
_scraper_import_error = None

try:
    from scraper_service.api.routers.scrape import router as scrape_router
    from scraper_service.browser.browser_pool import browser_pool

    SCRAPER_AVAILABLE = True
except ImportError as import_err:
    scrape_router = None
    browser_pool = None
    _scraper_import_error = str(import_err)

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info(f"[BOOT] Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"[BOOT] Environment: {settings.debug and 'development' or 'production'}")
    logger.info(f"[BOOT] Host: {settings.host}:{settings.port}")
    logger.info(f"[BOOT] MongoDB URI: {settings.mongodb_uri[:30]}...")
    logger.info(f"[BOOT] Backend URL: {settings.backend_url}")
    logger.info(f"[BOOT] Frontend URL: {settings.frontend_url or 'not set'}")
    logger.info(f"[BOOT] Scraper integrated: {SCRAPER_AVAILABLE}")

    if SCRAPER_AVAILABLE and browser_pool is not None:
        await browser_pool.start()
        logger.info("[BOOT] Playwright browser pool started ✓")
    elif not SCRAPER_AVAILABLE:
        logger.warning(
            "[BOOT] Scraper routes unavailable — %s",
            _scraper_import_error or "python-scraper package not found",
        )

    # Run X11 diagnostics only if not disabled
    if not settings.disable_x11_features:
        from app.services.whatsapp.x11_diagnostics import X11Diagnostics

        logger.info("[BOOT] Running X11/DISPLAY startup diagnostics...")
        diagnostics = X11Diagnostics.run_full_diagnostics()
        X11Diagnostics.log_diagnostics(diagnostics)

        if not diagnostics.get("x11_connection_ok"):
            logger.warning("[BOOT] X11 connection diagnostic failed — PyAutoGUI-based features may be unavailable")
            X11Diagnostics.log_remediation(diagnostics)
        else:
            logger.info("[BOOT] X11/DISPLAY diagnostics PASSED — PyAutoGUI ready")
    else:
        logger.info("[BOOT] X11/DISPLAY diagnostics DISABLED (cloud environment detected)")

    # Persistent MongoDB connection for background workers
    await db_connect(settings.mongodb_uri, settings.mongodb_database)
    from app.services.whatsapp.engine import whatsapp_engine
    from app.services.whatsapp.database import get_db
    from app.services.whatsapp.template_service import template_service
    whatsapp_engine.set_database(get_db())
    db = get_db()
    if db is not None:
        template_service.set_database(db)
        await template_service.load_templates(force=True)
        logger.info("[BOOT] WhatsApp template service initialized — templates loaded from MongoDB")
    logger.info("[BOOT] WhatsApp engine database initialized")

    logger.info(
        f"[BOOT] BACKEND_URL={settings.backend_url} PORT={settings.port} "
        f"HOST={settings.host} DEBUG={settings.debug} "
        f"MONGODB_URI={settings.mongodb_uri[:30]}..."
    )
    logger.info("[BOOT] REGISTERED ROUTES:")
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            logger.info(f"[ROUTE] {' '.join(route.methods)} {route.path}")
    logger.info(f"[BOOT] Router count: {len(app.routes)}")

    logger.info("[BOOT] WhatsApp routes registered: ✓")
    if SCRAPER_AVAILABLE:
        logger.info("[BOOT] Scraper routes registered: ✓")
    logger.info(f"[BOOT] {settings.app_name} started successfully")
    logger.info("=" * 50)
    yield
    logger.info("[SHUTDOWN] AI Analysis Service shutting down...")
    if SCRAPER_AVAILABLE and browser_pool is not None:
        logger.info("[SHUTDOWN] Closing browser pool...")
        await browser_pool.shutdown()
    await db_disconnect()
    logger.info("[SHUTDOWN] Service shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="FastAPI Smart Business Analysis and Lead Qualification Service",
    debug=settings.debug,
    lifespan=lifespan,
)

register_middleware(app)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url] if settings.frontend_url else ["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(analysis_router, prefix="/api/v1", tags=["analysis"])
app.include_router(whatsapp_router, prefix="/api/v1", tags=["whatsapp"])
app.include_router(whatsapp_api_router, prefix="/api/v1", tags=["whatsapp-api"])
if SCRAPER_AVAILABLE and scrape_router is not None:
    app.include_router(scrape_router, prefix="/api/v1", tags=["scrape"])


@app.get("/", summary="Root health check")
async def root_health() -> dict:
    return {
        "success": True,
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "scraper": "available" if SCRAPER_AVAILABLE else "unavailable",
        "endpoints": {
            "health": "/health",
            "analysis": "/api/v1/analyze-lead",
            "scrape": "/api/v1/scrape" if SCRAPER_AVAILABLE else None,
            "search": "/api/v1/search" if SCRAPER_AVAILABLE else None,
        },
    }


@app.get("/health", summary="Root health check alias")
async def root_health_alias():
    return {
        "success": True,
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }


def handle_sigterm(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    logger.info("Received SIGTERM, initiating graceful shutdown...")
    sys.exit(0)


def main(host: Optional[str] = None, port: Optional[int] = None) -> None:
    """
    Main function to run the AI Analysis Service.

    Args:
        host: Override host from settings
        port: Override port from settings
    """
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    from app.utils.logger import setup_logging
    setup_logging()

    run_host = host or settings.host
    run_port = int(port or os.getenv("PORT") or settings.port)

    logger.info(f"Starting server on {run_host}:{run_port}")

    import uvicorn
    uvicorn.run(
        "main:app",
        host=run_host,
        port=run_port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        workers=1,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI Analysis Service")
    parser.add_argument("--host", type=str, help="Host to bind to")
    parser.add_argument("--port", type=int, help="Port to listen on")

    args = parser.parse_args()

    main(host=args.host, port=args.port)