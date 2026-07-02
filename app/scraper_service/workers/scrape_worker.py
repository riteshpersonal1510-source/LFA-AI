"""
Scrape orchestrator — runs multiple sources concurrently and aggregates results.

Mirrors the behaviour of:
  backend/src/core/scraper-engine/scraper-engine.ts
  backend/src/services/scraper.service.ts
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from scraper_service.scrapers import (
    GoogleMapsScraper,
    JustDialScraper,
    IndiaMartScraper,
    ClutchScraper,
    WebsiteScraper,
)
from scraper_service.utils.logger import logger

MAX_CONCURRENCY: Dict[str, int] = {
    "google-maps": 1,
    "justdial": 1,
    "indiamart": 1,
    "clutch": 1,
    "website": 1,
}

_SCRAPER_MAP = {
    "google-maps": GoogleMapsScraper,
    "justdial": JustDialScraper,
    "indiamart": IndiaMartScraper,
    "clutch": ClutchScraper,
    "website": WebsiteScraper,
}


class ScrapeWorker:
    """Async multi-source scrape orchestrator."""

    async def run(
        self,
        keyword: str,
        sources: List[str],
        business_type: Optional[str] = None,
        location: str = "",
        area: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 0,
        max_results: Optional[int] = None,
        on_lead: Optional[Callable[[dict], Any]] = None,
        on_progress: Optional[Callable[[dict], Any]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        session_id = session_id or f"py_{uuid.uuid4().hex[:8]}"
        start_ts = time.time()

        valid_sources = [s for s in sources if s in _SCRAPER_MAP]
        if not valid_sources:
            return {
                "success": False,
                "message": f"No valid sources in {sources}",
                "sessionId": session_id,
                "totalExtracted": 0,
                "totalStored": 0,
                "totalDuplicates": 0,
                "sourceResults": [],
                "leads": [],
            }

        logger.info(
            "ScrapeWorker: Starting | keyword='{}' sources={} session={}",
            keyword,
            valid_sources,
            session_id,
        )

        all_leads: List[dict] = []
        source_results: List[dict] = []
        errors: List[dict] = []

        # Build tasks
        tasks = []
        for source in valid_sources:
            scraper_cls = _SCRAPER_MAP[source]
            tasks.append((source, scraper_cls()))

        # Run concurrently (respect per-source concurrency limits)
        semaphore = asyncio.Semaphore(2)  # max 2 sources at a time

        async def run_source(source: str, scraper) -> dict:
            async with semaphore:
                if is_cancelled and is_cancelled():
                    return {
                        "source": source,
                        "success": False,
                        "total_extracted": 0,
                        "total_stored": 0,
                        "total_duplicates": 0,
                        "leads": [],
                        "error": "cancelled",
                    }
                try:
                    return await scraper.scrape(
                        keyword=keyword,
                        business_type=business_type or keyword,
                        location=location,
                        area=area,
                        city=city,
                        state=state,
                        country=country,
                        session_id=session_id,
                        max_results=max_results or (limit if limit > 0 else None),
                        on_lead=on_lead,
                        on_progress=on_progress,
                    )
                except Exception as exc:
                    err_msg = str(exc)
                    logger.error(
                        "ScrapeWorker: source '{}' threw — {} | session={}",
                        source,
                        err_msg,
                        session_id,
                    )
                    return {
                        "source": source,
                        "success": False,
                        "total_extracted": 0,
                        "total_stored": 0,
                        "total_duplicates": 0,
                        "leads": [],
                        "error": err_msg,
                    }

        results = await asyncio.gather(
            *[run_source(src, scraper) for src, scraper in tasks],
            return_exceptions=False,
        )

        for i, result in enumerate(results):
            source = valid_sources[i]
            if isinstance(result, Exception):
                err_msg = str(result)
                errors.append({"source": source, "error": err_msg})
                source_results.append({
                    "source": source,
                    "totalExtracted": 0,
                    "totalStored": 0,
                    "totalDuplicates": 0,
                    "success": False,
                    "error": err_msg,
                })
                continue

            all_leads.extend(result.get("leads", []))
            source_results.append({
                "source": source,
                "totalExtracted": result.get("total_extracted", 0),
                "totalStored": result.get("total_stored", 0),
                "totalDuplicates": result.get("total_duplicates", 0),
                "success": result.get("success", False),
                "error": result.get("error"),
            })
            if result.get("error"):
                errors.append({"source": source, "error": result["error"]})

        total_extracted = sum(r["totalExtracted"] for r in source_results)
        total_stored = len(all_leads)
        total_duplicates = sum(r["totalDuplicates"] for r in source_results)
        any_success = any(r["success"] for r in source_results)
        elapsed = round(time.time() - start_ts, 2)

        message = (
            f"Scraping completed: {total_stored} leads from {', '.join(valid_sources)} in {elapsed}s"
            if any_success
            else f"All sources failed after {elapsed}s"
        )

        logger.info(
            "ScrapeWorker: Done | extracted={} stored={} dupes={} session={} elapsed={}s",
            total_extracted,
            total_stored,
            total_duplicates,
            session_id,
            elapsed,
        )

        return {
            "success": any_success or total_stored > 0,
            "message": message,
            "sessionId": session_id,
            "totalExtracted": total_extracted,
            "totalStored": total_stored,
            "totalDuplicates": total_duplicates,
            "sourceResults": source_results,
            "leads": all_leads,
            "errors": errors if errors else None,
        }
