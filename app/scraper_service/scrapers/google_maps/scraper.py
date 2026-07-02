from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.utils.extraction import calculate_lead_score
from scraper_service.utils.logger import logger


class GoogleMapsScraper(BaseScraper):
    name = "google-maps"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        if not await self.validate(ctx):
            return []
        query = ctx.business_type or ctx.keyword
        location = ctx.location or ctx.city or ctx.state or ctx.country or ""
        search_query = f"{query} in {location}" if location else query
        ctx.search_url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            await page.goto(ctx.search_url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_timeout(2500)
            cards = await page.evaluate(
                """() => {
                const selectors = ['div.Nv2PK', 'div[role="article"]'];
                const elements = [];
                for (const sel of selectors) {
                    const found = document.querySelectorAll(sel);
                    if (found.length > 0) { elements.push(...Array.from(found)); break; }
                }
                const leads = [];
                for (const card of elements) {
                    const nameEl = card.querySelector('.fontHeadlineSmall, div.qBF1Pd, div.fontHeadlineSmall');
                    const name = nameEl?.textContent?.trim() || '';
                    if (!name) continue;
                    const link = card.querySelector('a.hfpxzc');
                    const href = link?.getAttribute('href') || '';
                    const pidMatch = href.match(/maps\/place\/([^/]+)/);
                    const placeId = pidMatch ? decodeURIComponent(pidMatch[1]) : '';
                    leads.push({ companyName: name, sourceUrl: href, placeId, source: 'google-maps' });
                }
                return leads;
                }"""
            )
            # Return all available results - no artificial limits
            return cards
        except Exception as exc:  # noqa: BLE001
            await self._capture_failure_artifacts(ctx, exc, page)
            logger.error("{} discovery failed | error={}", self.name, exc)
            return []
        finally:
            await browser_pool.release(page, self.name)

    async def extract(self, ctx: ScrapeContext, discovered: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(item) for item in discovered]

    async def enrich(self, ctx: ScrapeContext, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for lead in leads:
            normalized = self._normalize_lead(dict(lead))
            normalized["searchedKeyword"] = ctx.keyword
            normalized["searchedLocation"] = ctx.location or ctx.city or ctx.state or ctx.country or None
            normalized["searchedCity"] = ctx.city
            normalized["searchedState"] = ctx.state
            normalized["searchedCountry"] = ctx.country
            normalized["fullSearchQuery"] = ctx.search_url or None
            normalized["businessType"] = ctx.business_type or ctx.keyword
            normalized["rating"] = None
            normalized["reviewsCount"] = None
            normalized["category"] = None
            normalized["address"] = None
            normalized["phone"] = None
            normalized["email"] = None
            normalized["website"] = None
            normalized["leadScore"] = calculate_lead_score(normalized)
            enriched.append(normalized)
        return enriched

    async def validate(self, ctx: ScrapeContext, lead: Optional[Dict[str, Any]] = None) -> bool:
        return bool((ctx.keyword or ctx.business_type) and (ctx.location or ctx.city or ctx.state or ctx.country))

    async def scrape(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        ctx = self._coerce_context(*args, **kwargs)
        try:
            discovered = await self._run_with_retries(ctx, self.discover)
            extracted = await self.extract(ctx, discovered)
            enriched = await self.enrich(ctx, extracted)
            return {
                "success": bool(enriched),
                "source": self.name,
                "total_extracted": len(enriched),
                "total_stored": len(enriched),
                "total_duplicates": 0,
                "leads": enriched,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("{} scrape failed | error={}", self.name, exc)
            return {"success": False, "source": self.name, "total_extracted": 0, "total_stored": 0, "total_duplicates": 0, "leads": [], "error": str(exc)}
