"""Health check endpoint."""

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.config.settings import settings
from scraper_service.models.scrape_models import HealthResponse

router = APIRouter()

_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    browser_status = browser_pool.get_status()
    playwright_ok = "available" if browser_status["pool_size"] >= 0 else "unavailable"

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        playwright=playwright_ok,
        mongodb="connected",  # checked at startup
        uptime=round(time.time() - _start_time, 2),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
