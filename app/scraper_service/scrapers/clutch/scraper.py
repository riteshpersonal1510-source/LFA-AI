"""
Clutch.co scraper — Python/Playwright implementation.

Reproduces: backend/src/sources/clutch/scraper.ts
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from playwright.async_api import Page

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.config.settings import MAX_LEADS_PER_SEARCH
from scraper_service.utils.extraction import calculate_lead_score
from scraper_service.utils.logger import logger

NAV_TIMEOUT = 30_000
SCROLL_WAIT_S = 2.0
MAX_PAGES = 10


class ClutchScraper(BaseScraper):
    name = "clutch"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        if not await self.validate(ctx):
            return []
        biz_type = ctx.business_type or ctx.keyword
        loc_str = ctx.city or ctx.location or "United States"
        ctx.search_url = f"https://clutch.co/search?q={quote_plus(biz_type)}" if not ctx.city else f"https://clutch.co/{loc_str.lower().replace(' ', '-')}/{biz_type.lower().replace(' ', '-')}"
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            await page.goto(ctx.search_url, wait_until="networkidle", timeout=NAV_TIMEOUT)
            await page.wait_for_timeout(2000)
            results = await self._extract_listings(page)
            
            # Enforce hard 20-lead limit
            effective_limit = min(ctx.max_results or MAX_LEADS_PER_SEARCH, MAX_LEADS_PER_SEARCH)
            return results[:effective_limit]
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
            normalized["fullSearchQuery"] = ctx.search_url or None
            normalized["businessType"] = ctx.business_type or ctx.keyword
            normalized["source"] = "clutch"
            normalized["leadScore"] = calculate_lead_score(normalized)
            enriched.append(normalized)
        return enriched

    async def validate(self, ctx: ScrapeContext, lead: Optional[Dict[str, Any]] = None) -> bool:
        return bool((ctx.keyword or ctx.business_type) and (ctx.location or ctx.city or ctx.country))

    async def scrape(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        ctx = self._coerce_context(*args, **kwargs)
        try:
            discovered = await self._run_with_retries(ctx, self.discover)
            extracted = await self.extract(ctx, discovered)
            enriched = await self.enrich(ctx, extracted)
            return {"success": bool(enriched), "source": self.name, "total_extracted": len(enriched), "total_stored": len(enriched), "total_duplicates": 0, "leads": enriched}
        except Exception as exc:  # noqa: BLE001
            logger.error("{} scrape failed | error={}", self.name, exc)
            return {"success": False, "source": self.name, "total_extracted": 0, "total_stored": 0, "total_duplicates": 0, "leads": [], "error": str(exc)}

    async def _extract_listings(self, page: Page) -> List[dict]:
        try:
            return await page.evaluate(
                """() => {
                const leads = [];
                const cards = document.querySelectorAll(
                    '.provider-row, .sg-provider-card, li.provider, ' +
                    'div[class*="provider"], div[class*="company-card"]'
                );

                for (const card of cards) {
                    const nameEl = card.querySelector(
                        '.company_title, .company-name, h3, h2, [class*="company"]'
                    );
                    const name = nameEl?.textContent?.trim() || '';
                    if (!name || name.length < 2) continue;

                    const ratingEl = card.querySelector(
                        '.rating, [class*="rating"], .sg-rating__value'
                    );
                    let rating = 0;
                    if (ratingEl) {
                        const rm = (ratingEl.textContent || '').match(/(\\d+\\.?\\d*)/);
                        if (rm) rating = parseFloat(rm[1]);
                    }

                    const reviewsEl = card.querySelector('[class*="review"]');
                    let reviews = 0;
                    if (reviewsEl) {
                        const rm = (reviewsEl.textContent || '').match(/(\\d+)/);
                        if (rm) reviews = parseInt(rm[1]);
                    }

                    const catEl = card.querySelector(
                        '.service_cluster, [class*="service"], [class*="category"], [class*="focus"]'
                    );
                    const category = catEl?.textContent?.trim() || '';

                    const locEl = card.querySelector(
                        '.locality, [class*="location"], [class*="address"]'
                    );
                    const address = locEl?.textContent?.trim() || '';

                    const linkEl = card.querySelector('a[href*="clutch.co"]');
                    const sourceUrl = linkEl?.getAttribute('href') || '';

                    const wsEl = card.querySelector(
                        'a[href^="http"]:not([href*="clutch.co"])'
                    );
                    const website = wsEl?.getAttribute('href') || null;

                    leads.push({
                        companyName: name,
                        rating: rating > 0 ? rating : null,
                        reviewsCount: reviews > 0 ? reviews : null,
                        category: category || null,
                        address: address || null,
                        website: website,
                        sourceUrl: sourceUrl || null,
                        source: 'clutch',
                    });
                }
                return leads;
            }"""
            )
        except Exception as exc:
            logger.debug("Clutch: _extract_listings error — {}", exc)
            return []

    async def _goto_next_page(self, page: Page) -> bool:
        try:
            next_btn = await page.query_selector(
                'a[rel="next"], .next-page, [aria-label="Next page"], button.next'
            )
            if next_btn:
                await next_btn.click()
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
        # Scroll fallback
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(SCROLL_WAIT_S)
        except Exception:
            pass
        return False
