from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.utils.extraction import calculate_lead_score, extract_emails, extract_phones, extract_social_links, extract_whatsapp_number, select_primary_phone
from scraper_service.utils.logger import logger

GOOGLE_SEARCH_URL = "https://www.google.com/search?q="
NAV_TIMEOUT = 20_000
CONTACT_PATHS = ["contact", "about", "team", "support", "contact-us", "about-us"]
EXCLUDED_DOMAINS = {"facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com", "wikipedia.org", "yelp.com", "justdial.com", "indiamart.com", "clutch.co", "google.com", "amazon.in", "amazon.com", "flipkart.com", "quora.com", "reddit.com"}


class WebsiteScraper(BaseScraper):
    name = "website"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2

    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        if not await self.validate(ctx):
            return []
        query = ctx.business_type or ctx.keyword
        location = ctx.location or ctx.city or ctx.state or ctx.country or ""
        search_query = f"{query} in {location} official website" if location else f"{query} official website"
        ctx.search_url = GOOGLE_SEARCH_URL + quote_plus(search_query)
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        try:
            await page.goto(ctx.search_url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
            await page.wait_for_timeout(2000)
            results = await page.evaluate("""(maxLinks) => { const results=[]; const links=document.querySelectorAll('div.g a[href^="http"]'); for (const el of links){ if(results.length >= maxLinks) break; const href=el.getAttribute('href')||''; const text=el.textContent?.trim()||''; if(href && !href.includes('google.com')) { const h3=el.querySelector('h3'); results.push({url: href, title: h3?.textContent || text}); } } return results; }""", max(5, ctx.max_results or 5))
            return self._filter_urls(results)
        except Exception as exc:  # noqa: BLE001
            await self._capture_failure_artifacts(ctx, exc, page)
            logger.error("{} discovery failed | error={}", self.name, exc)
            return []
        finally:
            await browser_pool.release(page, self.name)

    async def extract(self, ctx: ScrapeContext, discovered: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        page, _, _ = await browser_pool.acquire(self.name, self.browser_type)
        ctx.page = page
        leads: List[Dict[str, Any]] = []
        try:
            for item in discovered[: max(3, ctx.max_results or 3)]:
                url = item.get("url")
                if not url:
                    continue
                lead = await self._scrape_website(page, url, item.get("title") or "", ctx.business_type or ctx.keyword)
                if lead:
                    leads.append(lead)
            return leads
        finally:
            await browser_pool.release(page, self.name)

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
            normalized["source"] = "website"
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
            return {"success": bool(enriched), "source": self.name, "total_extracted": len(enriched), "total_stored": len(enriched), "total_duplicates": 0, "leads": enriched}
        except Exception as exc:  # noqa: BLE001
            logger.error("{} scrape failed | error={}", self.name, exc)
            return {"success": False, "source": self.name, "total_extracted": 0, "total_stored": 0, "total_duplicates": 0, "leads": [], "error": str(exc)}

    def _filter_urls(self, links: List[Dict[str, str]]) -> List[Dict[str, str]]:
        filtered: List[Dict[str, str]] = []
        for item in links:
            url = item.get("url", "").lower()
            try:
                host = urlparse(url).netloc.replace("www.", "")
            except Exception:
                continue
            if any(exc in host for exc in EXCLUDED_DOMAINS):
                continue
            filtered.append(item)
        return filtered

    async def _scrape_website(self, page, url: str, title: str, keyword: str) -> Optional[dict]:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
        except Exception:
            return None
        title_text = await page.title()
        company_name = self._extract_company_name(title_text or title, keyword)
        if not company_name:
            return None
        body_text = await page.evaluate("() => document.body?.innerText || ''")
        body_html = await page.content()
        all_links = await page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href') || '')")
        emails = extract_emails(body_text)
        phones = extract_phones(body_text)
        social_links = extract_social_links(all_links)
        whatsapp = extract_whatsapp_number(body_html)
        address = await self._extract_address(page)
        for path in CONTACT_PATHS:
            if emails and phones and address and social_links:
                break
            contact_url = url.rstrip("/") + f"/{path}"
            try:
                await page.goto(contact_url, wait_until="domcontentloaded", timeout=10_000)
                ct = await page.evaluate("() => document.body?.innerText || ''")
                ch = await page.content()
                cl = await page.evaluate("() => Array.from(document.querySelectorAll('a[href]')).map(a => a.getAttribute('href') || '')")
                if not emails:
                    emails = extract_emails(ct)
                if not phones:
                    phones = extract_phones(ct)
                if not social_links:
                    social_links = extract_social_links(cl)
                if not whatsapp:
                    whatsapp = extract_whatsapp_number(ch)
                if not address:
                    address = await self._extract_address(page)
            except Exception:
                continue
        primary_phone = select_primary_phone(phones)
        if whatsapp:
            social_links["whatsapp"] = whatsapp
        return {"companyName": company_name, "website": url, "email": emails[0] if emails else None, "phone": primary_phone or None, "address": address, "socialLinks": social_links or None, "sourceUrl": url}

    def _extract_company_name(self, title: str, keyword: str) -> Optional[str]:
        name = re.sub(r"\s*[-–|—]\s*.*$", "", title or "").strip()
        name = re.sub(r"\s*(Home|Official|Website)\s*$", "", name, flags=re.I).strip()
        return name if len(name) > 1 else None

    async def _extract_address(self, page) -> Optional[str]:
        selectors = ["[itemprop='address']", ".address", "#address", "[class*='address']", "footer"]
        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    text = (await el.inner_text()).strip()
                    if len(text) > 10:
                        return text
            except Exception:
                pass
        return None
