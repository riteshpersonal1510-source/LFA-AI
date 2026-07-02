"""
Main scrape router — the primary endpoint called by Node.js.

POST /api/v1/scrape
  Accepts a search request, runs all requested sources via ScrapeWorker,
  and returns structured lead data to Node.js for MongoDB storage.

POST /api/v1/scrape/source/{source}
  Run a single source scrape (used for targeted re-runs).

GET  /api/v1/scrape/health
  Quick scraper-level health check.

GET  /api/v1/browser/status
  Browser pool status.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.models.scrape_models import ScrapeRequest, ScrapeResponse, SourceResult, ScrapedLead
from scraper_service.session_manager import session_manager
from scraper_service.workers.scrape_worker import ScrapeWorker
from scraper_service.utils.logger import logger

router = APIRouter()
_worker = ScrapeWorker()


async def _execute_scrape(request: ScrapeRequest) -> ScrapeResponse:
    """Run scrape with session tracking for progress endpoints."""
    sources = [s for s in (request.sources or DEFAULT_SOURCES) if s in VALID_SOURCES]
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No valid sources. Allowed: {sorted(VALID_SOURCES)}",
        )

    session_id = request.sessionId or f"py_{uuid.uuid4().hex[:8]}"
    location = request.location or request.city or request.area or ""

    session_manager.create(
        keyword=request.keyword,
        location=location,
        session_id=session_id,
    )
    session_manager.mark_running(session_id, source=",".join(sources))

    logger.info(
        "[SCRAPE] Received | keyword='{}' sources={} session={}",
        request.keyword,
        sources,
        session_id,
    )

    def on_progress(payload: dict) -> None:
        session_manager.mark_progress(
            session_id,
            current_business=str(payload.get("currentBusiness") or payload.get("business") or ""),
            current_page=int(payload.get("currentPage") or payload.get("page") or 0),
            processed=int(payload.get("processed") or payload.get("found") or 0),
            total=int(payload.get("total") or payload.get("maxResults") or 0),
            saved=int(payload.get("saved") or 0),
            failed=int(payload.get("failed") or 0),
        )

    def on_lead(lead: dict) -> None:
        session_manager.update(
            session_id,
            current_business=str(lead.get("companyName") or ""),
            current_source=str(lead.get("source") or ""),
            processed=session_manager.get(session_id).processed + 1 if session_manager.get(session_id) else 1,
        )

    try:
        result = await _worker.run(
            keyword=request.keyword,
            sources=sources,
            business_type=request.businessType or request.keyword,
            location=request.location or "",
            area=request.area,
            city=request.city,
            state=request.state,
            country=request.country,
            session_id=session_id,
            limit=request.limit,
            max_results=request.maxResults,
            on_lead=on_lead,
            on_progress=on_progress,
        )
    except Exception as exc:
        session_manager.fail(session_id, str(exc))
        raise

    source_results = [
        SourceResult(
            source=sr["source"],
            totalExtracted=sr.get("totalExtracted", 0),
            totalStored=sr.get("totalStored", 0),
            totalDuplicates=sr.get("totalDuplicates", 0),
            success=sr.get("success", False),
            error=sr.get("error"),
        )
        for sr in result.get("sourceResults", [])
    ]

    leads = [ScrapedLead(**_safe_lead(lead)) for lead in result.get("leads", [])]
    total_stored = result.get("totalStored", len(leads))

    if result.get("success") or total_stored > 0:
        session_manager.complete(session_id, saved=total_stored)
    else:
        error_msg = ""
        if result.get("errors"):
            error_msg = "; ".join(
                f"{e.get('source', 'unknown')}: {e.get('error', '')}" for e in result["errors"]
            )
        session_manager.fail(session_id, error_msg or result.get("message", "Scrape failed"))

    return ScrapeResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        sessionId=session_id,
        totalExtracted=result.get("totalExtracted", 0),
        totalStored=total_stored,
        totalDuplicates=result.get("totalDuplicates", 0),
        sourceResults=source_results,
        leads=leads,
        errors=result.get("errors"),
    )

DEFAULT_SOURCES = ["google-maps", "justdial", "indiamart"]
VALID_SOURCES = {"google-maps", "justdial", "indiamart", "clutch", "website"}


# ---------------------------------------------------------------------------
# POST /api/v1/scrape   — main endpoint called by Node.js
# ---------------------------------------------------------------------------

@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run multi-source scrape",
    description=(
        "Triggered by Node.js search queue. "
        "Runs Playwright scrapers for requested sources and returns all extracted leads."
    ),
)
async def run_scrape(request: ScrapeRequest) -> ScrapeResponse:
    return await _execute_scrape(request)


# ---------------------------------------------------------------------------
# POST /api/v1/scraper/search — compatibility alias
# ---------------------------------------------------------------------------
@router.post(
    "/scraper/search",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run multi-source scrape via scraper/search alias",
    description=(
        "Compatibility alias for /api/v1/scrape. "
        "Preserves legacy contracts that expect /api/v1/scraper/search."
    ),
)
async def run_scraper_search(request: ScrapeRequest) -> ScrapeResponse:
    return await run_scrape(request)


# ---------------------------------------------------------------------------
# POST /api/v1/search — compatibility alias used by some clients
# ---------------------------------------------------------------------------
@router.post(
    "/search",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run search scrape",
    description="Compatibility alias for /api/v1/scrape.",
)
async def run_search(request: ScrapeRequest) -> ScrapeResponse:
    return await run_scrape(request)


# ---------------------------------------------------------------------------
# POST /api/v1/google-maps/search — Google Maps only scrape
# ---------------------------------------------------------------------------
@router.post(
    "/google-maps/search",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Google Maps scrape",
)
async def run_google_maps_search(request: ScrapeRequest) -> ScrapeResponse:
    request.sources = ["google-maps"]
    return await run_scrape(request)


# ---------------------------------------------------------------------------
# GET /api/v1/scraper/search-progress/{sessionId}
# ---------------------------------------------------------------------------
@router.get(
    "/scraper/search-progress/{session_id}",
    summary="Get scrape session progress",
    description="Never returns 404 — unknown sessions return status=unknown.",
)
async def get_search_progress(session_id: str):
    session = session_manager.get(session_id)
    if not session:
        return {
            "success": True,
            "data": {
                "sessionId": session_id,
                "status": "unknown",
                "completed": False,
                "percentage": 0,
                "message": "Session not found or expired",
            },
        }
    return {"success": True, "data": session.to_dict()}


# ---------------------------------------------------------------------------
# POST /api/v1/scrape/source/{source}   — single-source targeted run
# ---------------------------------------------------------------------------

@router.post(
    "/scrape/source/{source}",
    response_model=ScrapeResponse,
    status_code=status.HTTP_200_OK,
    summary="Run single-source scrape",
)
async def run_single_source(source: str, request: ScrapeRequest) -> ScrapeResponse:
    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source '{source}'. Allowed: {sorted(VALID_SOURCES)}",
        )

    request.sources = [source]
    return await run_scrape(request)


# ---------------------------------------------------------------------------
# GET /api/v1/browser/status
# ---------------------------------------------------------------------------

@router.get("/browser/status", summary="Browser pool status")
async def browser_status():
    return {"success": True, "data": browser_pool.get_status()}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_lead(lead: dict) -> dict:
    """Map raw scraper dict → ScrapedLead-compatible dict."""
    allowed_keys = {
        "companyName", "website", "phone", "email", "address", "category",
        "rating", "reviewsCount", "source", "sourceUrl", "placeId", "href",
        "city", "state", "area", "country", "businessType", "fullSearchQuery",
        "searchedKeyword", "searchedLocation", "searchedCity", "searchedState",
        "searchedArea", "searchedCountry", "searchedBusinessType",
        "latitude", "longitude", "pincode", "postalCode", "streetAddress",
        "workingHours", "businessStatus", "plusCode", "secondaryCategories",
        "serviceOptions", "ownerClaimed", "totalPhotos", "searchRank",
        "relevanceScore", "leadScore", "semanticKeyword",
    }
    clean = {k: v for k, v in lead.items() if k in allowed_keys and v is not None}
    clean.setdefault("source", "unknown")
    clean.setdefault("companyName", "Unknown")
    return clean
