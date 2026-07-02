"""
IndiaMART scraper — Python/Playwright implementation.

Reproduces:
  backend/src/modules/scrapers/indiamart/indiamart.scraper.ts
  backend/src/sources/indiamart/scraper.ts
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from playwright.async_api import Page

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.utils.extraction import calculate_lead_score
from scraper_service.utils.logger import logger

SEARCH_URL_TPL = "https://dir.indiamart.com/search.mp?ss={query}"
PROFILE_TIMEOUT = 15_000
NAV_TIMEOUT = 30_000
MAX_STALLED = 30
SCROLL_WAIT_S = 1.5


class IndiaMartScraper(BaseScraper):
    name = "indiamart"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        if not await self.validate(ctx):
            return []
        query_parts = [ctx.business_type or ctx.keyword]
        if ctx.area:
            query_parts.append(ctx.area)
        if ctx.city:
            query_parts.append(ctx.city)
        ctx.search_url = SEARCH_URL_TPL.format(query=quote_plus(" ".join(query_parts)))
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            await page.goto(ctx.search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            await page.wait_for_timeout(3000)
            return await self._extract_listings(page)
        except Exception as exc:  # noqa: BLE001
            await self._capture_failure_artifacts(ctx, exc, page)
            logger.error("{} discovery failed | error={}", self.name, exc)
            return []
        finally:
            await browser_pool.release(page, self.name)

    async def extract(self, ctx: ScrapeContext, discovered: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            for listing in discovered:
                profile_url = listing.get("profileUrl")
                if profile_url:
                    try:
                        enriched = await self._scrape_profile(page, profile_url)
                        listing.update({k: v for k, v in enriched.items() if v})
                    except Exception as exc:  # noqa: BLE001
                        logger.debug("{} profile enrich failed '{}' — {}", self.name, listing.get("companyName"), exc)
                results.append(dict(listing))
            return results
        finally:
            await browser_pool.release(page, self.name)

    async def enrich(self, ctx: ScrapeContext, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for lead in leads:
            normalized = self._normalize_lead(dict(lead))
            normalized["searchedKeyword"] = ctx.keyword
            normalized["searchedLocation"] = ctx.location or ctx.city or ctx.state or ctx.country or None
            normalized["searchedArea"] = ctx.area
            normalized["searchedCity"] = ctx.city
            normalized["searchedState"] = ctx.state
            normalized["fullSearchQuery"] = ctx.search_url or None
            normalized["businessType"] = ctx.business_type or ctx.keyword
            normalized["source"] = "indiamart"
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

    # ------------------------------------------------------------------
    # Listing grid extraction
    # ------------------------------------------------------------------

    async def _extract_listings(self, page: Page) -> List[dict]:
        try:
            return await page.evaluate(
                """() => {
                const results = [];
                const cards = document.querySelectorAll(
                    '.cardLinks, .bsrCatalog, .listing-card, ' +
                    'div[class*="listingCard"], div[class*="listing_card"], ' +
                    'div[class*="catalogCard"], div[class*="card"]'
                );

                for (const card of cards) {
                    const nameEl = card.querySelector(
                        'a.company-name, .companyName, h3.companyName, ' +
                        '[class*="companyName"], [class*="company_name"], h3, h2'
                    );
                    const name = nameEl?.textContent?.trim() || '';
                    if (!name || name.length < 2) continue;

                    // Profile URL
                    const linkEl = card.querySelector('a[href*="indiamart.com"]');
                    const profileUrl = linkEl?.getAttribute('href') || null;

                    // Phone
                    const telEl = card.querySelector('a[href^="tel:"]');
                    let phone = telEl?.getAttribute('href')?.replace('tel:', '') || '';
                    if (!phone) {
                        const pm = (card.textContent || '').match(/(\\+?91[\\s-]?)?[6-9]\\d{9}/);
                        if (pm) phone = pm[0].replace(/[\\s-]/g, '');
                    }

                    // Address / location
                    const locEl = card.querySelector(
                        '.lcAddress, [class*="address"], [class*="location"], .location'
                    );
                    const address = locEl?.textContent?.trim() || '';

                    // Category / product
                    const catEl = card.querySelector(
                        '.clsCatg, [class*="category"], [class*="product"], .product-name'
                    );
                    const category = catEl?.textContent?.trim() || '';

                    // Website
                    const wsEl = card.querySelector(
                        'a[href^="http"]:not([href*="indiamart.com"]):not([href*="facebook"])'
                    );
                    const website = wsEl?.getAttribute('href') || null;

                    results.push({
                        companyName: name,
                        phone: phone || null,
                        website: website,
                        address: address || null,
                        category: category || null,
                        profileUrl: profileUrl,
                        source: 'indiamart',
                        sourceUrl: profileUrl,
                    });
                }
                return results;
            }"""
            )
        except Exception as exc:
            logger.debug("IndiaMART: _extract_listings error — {}", exc)
            return []

    async def _scrape_profile(self, page: Page, profile_url: str) -> dict:
        """Visit a company profile page to extract richer contact data."""
        enriched: dict = {}
        try:
            await page.goto(profile_url, wait_until="domcontentloaded", timeout=PROFILE_TIMEOUT)
            await page.wait_for_timeout(1500)

            data = await page.evaluate(
                """() => {
                const result = {};

                // Phone
                const telEl = document.querySelector('a[href^="tel:"]');
                if (telEl) result.phone = telEl.getAttribute('href').replace('tel:', '');

                // Email
                const emailEl = document.querySelector('a[href^="mailto:"]');
                if (emailEl) result.email = emailEl.getAttribute('href').replace('mailto:', '');

                // Website
                const wsEl = document.querySelector(
                    'a.website-link, a[href^="http"]:not([href*="indiamart.com"])'
                );
                if (wsEl) result.website = wsEl.getAttribute('href');

                // Address
                const addrEl = document.querySelector(
                    '[class*="address"], [itemprop="address"], .address'
                );
                if (addrEl) result.address = addrEl.textContent?.trim();

                // GST
                const gstEl = document.querySelector('[class*="gst"], [class*="GST"]');
                if (gstEl) result.gst = gstEl.textContent?.trim();

                return result;
            }"""
            )
            enriched.update(data)

            # Return to search results
            await page.go_back(wait_until="domcontentloaded", timeout=10_000)
        except Exception:
            pass
        return enriched

    async def _scroll_page(self, page: Page) -> None:
        try:
            await page.evaluate(
                """() => {
                window.scrollBy(0, Math.max(600, window.innerHeight * 0.8));
            }"""
            )
        except Exception:
            pass
