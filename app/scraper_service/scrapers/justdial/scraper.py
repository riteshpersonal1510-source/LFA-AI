"""
JustDial scraper — Python/Playwright implementation.

Reproduces:
  backend/src/core/scraper-engine/sources/justdial/scraper.ts
  backend/src/sources/justdial/scraper.ts

JustDial requires Firefox (Chromium hits ERR_HTTP2_PROTOCOL_ERROR).
"""

from __future__ import annotations

import asyncio
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

from playwright.async_api import Page

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.utils.extraction import calculate_lead_score
from scraper_service.utils.logger import logger
from .selectors import MENU_ITEM_PATTERNS

MAX_STALLED = 50
SCROLL_WAIT_S = 1.5


def _is_menu_item(name: str) -> bool:
    lower = name.lower().strip()
    if len(lower) < 6:
        return True
    if any(p in lower for p in MENU_ITEM_PATTERNS):
        return True
    if re.match(r"^\d+\s", lower):
        return True
    if re.match(r"^(Rs\.?|₹)", lower):
        return True
    return False


def _random_delay(lo: float = 2.5, hi: float = 4.5) -> float:
    return random.uniform(lo, hi)


class JustDialScraper(BaseScraper):
    name = "justdial"
    browser_type = "firefox"
    timeout_s = 60
    max_retries = 2

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        if not await self.validate(ctx):
            return []
        biz_type = ctx.business_type or ctx.keyword
        city_slug = ctx.city.lower().replace(" ", "-") if ctx.city else ""
        area_slug = ctx.area.lower().replace(" ", "-") if ctx.area else ""
        biz_slug = biz_type.lower().replace(" ", "-")
        ctx.search_url = f"https://www.justdial.com/{city_slug}/{biz_slug}-in-{area_slug}" if ctx.city and ctx.area else (f"https://www.justdial.com/{city_slug}/{biz_slug}" if ctx.city else f"https://www.justdial.com/search?q={quote_plus(biz_type)}")
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            await page.goto(ctx.search_url, wait_until="domcontentloaded", timeout=45_000)
            await asyncio.sleep(_random_delay(3.0, 5.0))
            return await self._extract_visible(page)
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
            normalized["searchedArea"] = ctx.area
            normalized["searchedCity"] = ctx.city
            normalized["searchedState"] = ctx.state
            normalized["fullSearchQuery"] = ctx.search_url or None
            normalized["businessType"] = ctx.business_type or ctx.keyword
            normalized["source"] = "justdial"
            normalized["leadScore"] = calculate_lead_score(normalized)
            enriched.append(normalized)
        return enriched

    async def validate(self, ctx: ScrapeContext, lead: Optional[Dict[str, Any]] = None) -> bool:
        return bool((ctx.keyword or ctx.business_type) and (ctx.city or ctx.location or ctx.country))

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
    # Page extraction
    # ------------------------------------------------------------------

    async def _extract_visible(self, page: Page) -> List[dict]:
        try:
            return await page.evaluate(
                """() => {
                const leads = [];
                const boxes = document.querySelectorAll('div[class*="resultbox"]');

                for (const box of boxes) {
                    const text = box.textContent || '';

                    const nameEl = box.querySelector('.font22, span[class*="font22"], [class*="store_name"], .lng_cont_name, h2');
                    const name = nameEl?.textContent?.trim() || '';
                    if (!name || name.length < 3) continue;

                    // Phone
                    const telLink = box.querySelector('a[href^="tel:"]');
                    let phone = telLink?.getAttribute('href')?.replace('tel:', '') || '';
                    if (!phone) {
                        const callEl = box.querySelector('.callNowAnchor, a[class*="call"], [class*="callNow"]');
                        if (callEl) phone = (callEl.textContent || '').replace(/^Call\\s+/i, '').replace(/[\\s-]/g, '');
                    }
                    if (!phone) {
                        const pm = text.match(/(\\+?91[\\s-]?)?[6-9]\\d{9}/);
                        if (pm) phone = pm[0].replace(/[\\s-]/g, '');
                    }

                    // Address
                    const addrEl = box.querySelector('.cont_fload, [class*="address"], .mre-dir');
                    const address = addrEl?.textContent?.trim() || '';

                    // Rating
                    const ratingEl = box.querySelector('[class*="rating"], .green-box, [class*="green"]');
                    let rating = 0;
                    if (ratingEl) {
                        const rm = (ratingEl.textContent || '').match(/(\\d+\\.?\\d*)/);
                        if (rm) rating = parseFloat(rm[1]);
                    }

                    // Source URL
                    const hrefEl = box.querySelector('a[href*="justdial.com"]');
                    const href = hrefEl?.getAttribute('href') || '';
                    const sourceUrl = href.startsWith('http') ? href : ('https://www.justdial.com' + href);

                    // Website (external link)
                    const wsEl = box.querySelector('a[href^="http"]:not([href*="justdial.com"]):not([href*="facebook"]):not([href*="instagram"])');
                    const website = wsEl?.getAttribute('href') || null;

                    leads.push({
                        companyName: name,
                        phone: phone || null,
                        website: website,
                        address: address || null,
                        rating: (rating > 0 && rating < 10) ? rating : null,
                        source: 'justdial',
                        sourceUrl: sourceUrl || null,
                    });
                }

                // Fallback selector
                if (leads.length === 0) {
                    const alt = document.querySelectorAll('div[class*="result"], section[class*="result"]');
                    for (const box of alt) {
                        const nameEl = box.querySelector('.font22, h2, h3, [class*="name"]');
                        const name = nameEl?.textContent?.trim() || '';
                        if (!name || name.length < 3) continue;
                        const pm = (box.textContent || '').match(/(\\+?91[\\s-]?)?[6-9]\\d{9}/);
                        const phone = pm ? pm[0].replace(/[\\s-]/g, '') : null;
                        const addr = box.querySelector('[class*="address"]')?.textContent?.trim() || null;
                        leads.push({ companyName: name, phone, address: addr, source: 'justdial' });
                    }
                }

                return leads;
            }"""
            )
        except Exception as exc:
            logger.debug("JustDial: _extract_visible error — {}", exc)
            return []

    async def _scroll_page(self, page: Page) -> None:
        try:
            await page.evaluate(
                """() => {
                const sels = ['.result-list', '[class*="result_list"]', '.search-result',
                              'main', '[role="main"]', '.list_part', 'body'];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (el) { el.scrollTop = el.scrollHeight; return; }
                }
                window.scrollBy(0, 600);
            }"""
            )
        except Exception:
            pass
