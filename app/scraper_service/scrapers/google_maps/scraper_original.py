from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, parse_qs, urlparse

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.utils.extraction import calculate_lead_score, parse_address_components, extract_coordinates_from_url
from scraper_service.utils.logger import logger
from .selectors import *


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
            
            # Get initial card list
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
                    leads.push({ companyName: name, sourceUrl: href, placeId, source: 'google-maps', cardIndex: leads.length });
                }
                return leads;
                }"""
            )
            
            if not cards:
                logger.warning("No cards found for query: {}", search_query)
                return []
            
            # Limit results if max_results is specified
            max_results = ctx.max_results or len(cards)
            cards_to_process = cards[:max_results]
            
            logger.info("Found {} cards, processing {} with detailed extraction", len(cards), len(cards_to_process))
            
            # Extract detailed information for each business
            detailed_leads = []
            for i, card in enumerate(cards_to_process):
                try:
                    # Timeout per lead to avoid stalling the whole batch
                    detailed_lead = await asyncio.wait_for(
                        self._extract_business_details(page, card, i),
                        timeout=15.0
                    )
                    if detailed_lead:
                        detailed_leads.append(detailed_lead)
                        logger.debug("Extracted details for: {}", detailed_lead.get('companyName', 'Unknown'))
                except asyncio.TimeoutError:
                    logger.warning("Timeout extracting details for business {}: {}", i, card.get('companyName', 'Unknown'))
                    # Keep basic info on timeout
                    detailed_leads.append(card)
                except Exception as e:
                    logger.warning("Error extracting details for business {}: {} - {}", i, card.get('companyName', 'Unknown'), str(e))
                    # Keep basic info on error
                    detailed_leads.append(card)
            
            return detailed_leads
            
        except Exception as exc:  # noqa: BLE001
            await self._capture_failure_artifacts(ctx, exc, page)
            logger.error("{} discovery failed | error={}", self.name, exc)
            return []
        finally:
            await browser_pool.release(page, self.name)

    async def _extract_business_details(self, page, card: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Extract detailed information by clicking into the business detail panel."""
        try:
            # Navigate back to search results if not on first card
            if index > 0:
                await page.go_back(wait_until="domcontentloaded", timeout=5000)
                await page.wait_for_timeout(1000)
            
            # Click on the business card to open detail panel
            card_selector = f'div.Nv2PK:nth-child({index + 1}), div[role="article"]:nth-child({index + 1})'
            try:
                await page.click(card_selector, timeout=5000)
            except Exception:
                # Fallback: try to navigate directly via URL if clicking fails
                if card.get('sourceUrl'):
                    await page.goto(card['sourceUrl'], wait_until="domcontentloaded", timeout=10000)
                else:
                    logger.warning("Could not click or navigate to business {}", card.get('companyName', 'Unknown'))
                    return card
            
            # Wait for detail panel to load
            await page.wait_for_timeout(2000)
            
            # Extract all details
            details = {
                'companyName': card.get('companyName'),
                'sourceUrl': await self._get_current_maps_url(page),
                'placeId': card.get('placeId'),
                'source': 'google-maps'
            }
            
            # Extract each field with individual try/catch
            details.update(await self._extract_category(page))
            details.update(await self._extract_address_and_location(page))
            details.update(await self._extract_contact_info(page))
            details.update(await self._extract_rating_and_reviews(page))
            details.update(await self._extract_business_status_and_hours(page))
            details.update(await self._extract_additional_info(page))
            details.update(await self._extract_coordinates(page))
            
            return details
            
        except Exception as e:
            logger.warning("Failed to extract business details for {}: {}", card.get('companyName', 'Unknown'), str(e))
            return card

    async def _get_current_maps_url(self, page) -> str:
        """Get the current Google Maps URL."""
        try:
            return page.url
        except Exception:
            return ""

    async def _extract_category(self, page) -> Dict[str, Any]:
        """Extract business category."""
        try:
            for selector in DETAIL_CATEGORY:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        category = await element.inner_text()
                        if category and category.strip():
                            return {'category': category.strip()}
                except Exception:
                    continue
        except Exception:
            pass
        return {'category': None}

    async def _extract_address_and_location(self, page) -> Dict[str, Any]:
        """Extract address and parse into components."""
        try:
            for selector in DETAIL_ADDRESS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        address_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if address_text and address_text.strip():
                            # Clean up address text
                            address = re.sub(r'^(Address: |Address )', '', address_text.strip())
                            
                            # Parse address components
                            components = parse_address_components(address)
                            
                            return {
                                'address': address,
                                'area': components.get('area'),
                                'city': components.get('city'),
                                'state': components.get('state'),
                                'country': components.get('country'),
                                'pincode': components.get('pincode'),
                                'postalCode': components.get('pincode'),  # Alias for pincode
                            }
                except Exception:
                    continue
        except Exception:
            pass
        return {
            'address': None, 'area': None, 'city': None, 'state': None, 
            'country': None, 'pincode': None, 'postalCode': None
        }

    async def _extract_contact_info(self, page) -> Dict[str, Any]:
        """Extract phone and website."""
        result = {'phone': None, 'website': None}
        
        # Extract phone
        try:
            for selector in DETAIL_PHONE:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        phone_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if phone_text:
                            # Clean phone number
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)\.]+', phone_text)
                            if phone_match:
                                result['phone'] = phone_match.group().strip()
                                break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract website
        try:
            for selector in DETAIL_WEBSITE:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        href = await element.get_attribute('href')
                        if href:
                            # Resolve Google redirect URLs
                            if 'google.com/url' in href and 'q=' in href:
                                parsed = urlparse(href)
                                query_params = parse_qs(parsed.query)
                                if 'q' in query_params:
                                    result['website'] = query_params['q'][0]
                            else:
                                result['website'] = href
                            break
                except Exception:
                    continue
        except Exception:
            pass
            
        return result

    async def _extract_rating_and_reviews(self, page) -> Dict[str, Any]:
        """Extract rating and review count from aria-label."""
        try:
            for selector in DETAIL_RATING:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        aria_label = await element.get_attribute('aria-label')
                        if aria_label:
                            # Parse "4.5 stars 128 Reviews" format
                            rating_match = re.search(r'(\d+\.?\d*)\s*stars?', aria_label)
                            review_match = re.search(r'(\d+)\s*reviews?', aria_label, re.IGNORECASE)
                            
                            rating = float(rating_match.group(1)) if rating_match else None
                            reviews = int(review_match.group(1)) if review_match else None
                            
                            return {
                                'rating': rating,
                                'reviewsCount': reviews
                            }
                except Exception:
                    continue
        except Exception:
            pass
        return {'rating': None, 'reviewsCount': None}

    async def _extract_business_status_and_hours(self, page) -> Dict[str, Any]:
        """Extract business status (open/closed) and working hours."""
        result = {'businessStatus': None, 'workingHours': None}
        
        # Extract business status
        try:
            for selector in DETAIL_BUSINESS_STATUS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        status_text = await element.inner_text()
                        if status_text and any(word in status_text.lower() for word in ['open', 'closed', 'closes', 'opens']):
                            result['businessStatus'] = status_text.strip()
                            break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract working hours
        try:
            for selector in DETAIL_WORKING_HOURS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        hours_text = await element.inner_text()
                        if hours_text and len(hours_text.strip()) > 5:
                            result['workingHours'] = hours_text.strip()
                            break
                except Exception:
                    continue
        except Exception:
            pass
            
        return result

    async def _extract_additional_info(self, page) -> Dict[str, Any]:
        """Extract plus code, owner claimed status, total photos, service options."""
        result = {
            'plusCode': None,
            'ownerClaimed': None,
            'totalPhotos': None,
            'serviceOptions': None,
            'secondaryCategories': None
        }
        
        # Extract plus code
        try:
            for selector in DETAIL_PLUS_CODE:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        plus_code_text = await element.inner_text()
                        if plus_code_text and re.match(r'^[A-Z0-9+]+$', plus_code_text.replace(' ', '')):
                            result['plusCode'] = plus_code_text.strip()
                            break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Check if owner claimed (look for "Claim this business" button - if absent, likely claimed)
        try:
            claim_button = await page.query_selector('button[aria-label*="Claim this business"]')
            result['ownerClaimed'] = claim_button is None
        except Exception:
            pass
        
        # Extract total photos count
        try:
            for selector in DETAIL_TOTAL_PHOTOS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        photos_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if photos_text:
                            photos_match = re.search(r'(\d+)\s*photos?', photos_text, re.IGNORECASE)
                            if photos_match:
                                result['totalPhotos'] = int(photos_match.group(1))
                                break
                except Exception:
                    continue
        except Exception:
            pass
        
        # Extract service options
        try:
            for selector in DETAIL_SERVICE_OPTIONS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        service_text = await element.inner_text()
                        if service_text and len(service_text.strip()) > 3:
                            # Split into list if contains common separators
                            if any(sep in service_text for sep in [',', '•', '\n']):
                                services = [s.strip() for s in re.split(r'[,•\n]', service_text) if s.strip()]
                                result['serviceOptions'] = services
                            else:
                                result['serviceOptions'] = [service_text.strip()]
                            break
                except Exception:
                    continue
        except Exception:
            pass
            
        return result

    async def _extract_coordinates(self, page) -> Dict[str, Any]:
        """Extract latitude and longitude from URL."""
        try:
            current_url = page.url
            lat, lng = extract_coordinates_from_url(current_url)
            return {
                'latitude': lat,
                'longitude': lng
            }
        except Exception:
            pass
        return {'latitude': None, 'longitude': None}

    async def extract(self, ctx: ScrapeContext, discovered: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [dict(item) for item in discovered]

    async def enrich(self, ctx: ScrapeContext, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich leads with additional data and email extraction."""
        enriched: List[Dict[str, Any]] = []
        
        # Import website scraper for email extraction
        try:
            from ..website.scraper import WebsiteScraper
            website_scraper = WebsiteScraper()
        except ImportError:
            website_scraper = None
            logger.warning("Could not import WebsiteScraper for email extraction")
        
        for lead in leads:
            normalized = self._normalize_lead(dict(lead))
            
            # Set search context
            normalized["searchedKeyword"] = ctx.keyword
            normalized["searchedLocation"] = ctx.location or ctx.city or ctx.state or ctx.country or None
            normalized["searchedCity"] = ctx.city
            normalized["searchedState"] = ctx.state
            normalized["searchedCountry"] = ctx.country
            normalized["fullSearchQuery"] = ctx.search_url or None
            normalized["businessType"] = ctx.business_type or ctx.keyword
            
            # Extract email from website if website is available
            if normalized.get("website") and website_scraper:
                try:
                    email = await website_scraper.extract_email_from_website(normalized["website"])
                    normalized["email"] = email
                except Exception as e:
                    logger.warning("Failed to extract email for {}: {}", normalized.get("companyName", "Unknown"), str(e))
                    normalized["email"] = None
            else:
                normalized["email"] = None
            
            # Calculate lead score with all the extracted data
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
