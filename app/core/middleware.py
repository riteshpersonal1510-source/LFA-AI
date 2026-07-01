"""Custom middleware for the AI Analysis Service."""

import asyncio
import time
import logging
from typing import Callable

from fastapi import Request, Response

REQUEST_TIMEOUT_SECONDS = 60


async def request_timing_middleware(
    request: Request, call_next: Callable
) -> Response:
    """Add request timing information to response."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


async def request_logging_middleware(
    request: Request, call_next: Callable
) -> Response:
    """Log incoming requests."""
    logger = logging.getLogger(__name__)
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response


async def request_timeout_middleware(
    request: Request, call_next: Callable
) -> Response:
    """Enforce request timeout to prevent long-running requests from freezing the service."""
    try:
        response = await asyncio.wait_for(
            call_next(request),
            timeout=REQUEST_TIMEOUT_SECONDS
        )
        return response
    except asyncio.TimeoutError:
        logger = logging.getLogger(__name__)
        logger.warning(f"Request timed out after {REQUEST_TIMEOUT_SECONDS}s: {request.method} {request.url.path}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=504,
            content={
                "success": False,
                "message": f"Request timed out after {REQUEST_TIMEOUT_SECONDS} seconds",
                "error": {
                    "code": 504,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                },
            },
        )


def register_middleware(app) -> None:
    """Register all middleware with the FastAPI app."""
    app.middleware("http")(request_timeout_middleware)
    app.middleware("http")(request_timing_middleware)
    app.middleware("http")(request_logging_middleware)
