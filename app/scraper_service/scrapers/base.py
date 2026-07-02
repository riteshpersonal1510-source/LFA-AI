from __future__ import annotations

import asyncio
import os
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from playwright.async_api import Page

from scraper_service.utils.logger import logger


@dataclass
class ScrapeContext:
    keyword: str
    business_type: Optional[str] = None
    location: str = ""
    area: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    session_id: Optional[str] = None
    max_results: Optional[int] = None
    source: str = "unknown"
    search_url: str = ""
    browser_type: str = "chromium"
    metadata: Dict[str, Any] = field(default_factory=dict)
    page: Optional[Page] = None


class BaseScraper:
    name = "base"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2

    def __init__(self, browser_pool=None) -> None:
        self.browser_pool = browser_pool
        self.debug_dir = Path(__file__).resolve().parents[2] / "logs" / "debug" / self.name
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def _coerce_context(self, *args: Any, **kwargs: Any) -> ScrapeContext:
        if args and isinstance(args[0], ScrapeContext):
            return args[0]

        keyword = kwargs.get("keyword") or ""
        if not keyword and args and isinstance(args[0], str):
            keyword = args[0]

        business_type = kwargs.get("business_type") or kwargs.get("businessType")
        location = kwargs.get("location") or ""
        area = kwargs.get("area")
        city = kwargs.get("city")
        state = kwargs.get("state")
        country = kwargs.get("country")
        session_id = kwargs.get("session_id") or kwargs.get("sessionId")
        max_results = kwargs.get("max_results") or kwargs.get("maxResults")

        return ScrapeContext(
            keyword=keyword,
            business_type=business_type,
            location=location,
            area=area,
            city=city,
            state=state,
            country=country,
            session_id=session_id,
            max_results=max_results,
            source=self.name,
        )

    def _normalize_optional(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return None
            lowered = cleaned.lower()
            if lowered in {"n/a", "na", "none", "null", "unknown", "not available", "-", "--"}:
                return None
            return cleaned
        return str(value)

    def _normalize_lead(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(lead)
        for key in ["companyName", "website", "phone", "email", "address", "category", "sourceUrl", "source"]:
            if key in normalized and isinstance(normalized[key], str):
                normalized[key] = self._normalize_optional(normalized[key])
        for key in ["city", "state", "area", "country", "businessType", "searchedKeyword", "searchedLocation", "searchedCity", "searchedState", "searchedArea", "searchedCountry", "searchedBusinessType", "fullSearchQuery"]:
            if key in normalized and isinstance(normalized[key], str):
                normalized[key] = self._normalize_optional(normalized[key])
        if normalized.get("companyName") is None:
            normalized["companyName"] = "Unknown"
        normalized["source"] = normalized.get("source") or self.name
        if normalized.get("source") == "unknown":
            normalized["source"] = self.name
        return normalized

    async def _run_with_retries(self, ctx: ScrapeContext, func: Callable[[ScrapeContext], Any]) -> Any:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return await asyncio.wait_for(func(ctx), timeout=self.timeout_s)
            except asyncio.TimeoutError as exc:
                last_error = exc
                logger.warning("{} timeout on attempt {}/{} | session={}", self.name, attempt + 1, self.max_retries + 1, ctx.session_id)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("{} attempt {}/{} failed | error={} | session={}", self.name, attempt + 1, self.max_retries + 1, exc, ctx.session_id)
            if attempt < self.max_retries:
                await asyncio.sleep(1.5 * (attempt + 1))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"{self.name} execution failed")

    async def _capture_failure_artifacts(self, ctx: ScrapeContext, error: Exception, page: Optional[Page] = None) -> None:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        ts = asyncio.get_running_loop().time()
        screenshot_path = self.debug_dir / f"{ctx.source}-{int(ts)}.png"
        html_path = self.debug_dir / f"{ctx.source}-{int(ts)}.html"
        if page is not None:
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception as exc:  # noqa: BLE001
                logger.warning("{} screenshot capture failed | error={}", self.name, exc)
            try:
                html = await page.content()
                html_path.write_text(html, encoding="utf-8")
            except Exception as exc:  # noqa: BLE001
                logger.warning("{} html dump failed | error={}", self.name, exc)
        error_path = self.debug_dir / f"{ctx.source}-{int(ts)}.txt"
        error_path.write_text(
            f"{self.name}\n{ctx.session_id or 'unknown'}\n{traceback.format_exc()}",
            encoding="utf-8",
        )
        logger.error("{} failure artifacts saved | screenshot={} | html={} | error={}", self.name, screenshot_path.name, html_path.name, error)

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        return []

    async def extract(self, ctx: ScrapeContext, discovered: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return list(discovered)

    async def enrich(self, ctx: ScrapeContext, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [self._normalize_lead(lead) for lead in leads]

    async def validate(self, ctx: ScrapeContext, lead: Optional[Dict[str, Any]] = None) -> bool:
        if not ctx.keyword and not ctx.business_type:
            return False
        if not (ctx.location or ctx.city or ctx.state or ctx.country):
            return False
        return True

    async def scrape(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        return {
            "success": False,
            "source": self.name,
            "total_extracted": 0,
            "total_stored": 0,
            "total_duplicates": 0,
            "leads": [],
            "error": "Base scraper implementation not overridden",
        }
