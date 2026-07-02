"""
Enhanced Google Maps scraper with robust extraction, retry logic, and data quality monitoring.

IMPORTANT: Field availability depends on what each business has actually published on Google Maps.
Fill-rates will vary by category/region. This code maximizes extraction reliability but cannot 
guarantee complete data for fields that businesses simply don't provide.
"""

from __future__ import annotations

import asyncio
import re
import random
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, parse_qs, urlparse

from tenacity import retry, stop_after_attempt, wait_exponential
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from scraper_service.browser.browser_pool import browser_pool
from scraper_service.scrapers.base import BaseScraper, ScrapeContext
from scraper_service.models.scrape_models import DataQuality
from scraper_service.config.settings import MAX_LEADS_PER_SEARCH
from scraper_service.utils.extraction import calculate_lead_score, parse_address_components, extract_coordinates_from_url
from scraper_service.utils.logger import logger
from .selectors import *


# Data quality thresholds - log warnings if fill rates drop below these
FILL_RATE_THRESHOLDS = {
    'phone': 0.30,  # 30%
    'website': 0.25,  # 25% 
    'address': 0.40,  # 40%
    'rating': 0.60,  # 60%
    'category': 0.70,  # 70%
}

# Rate limiting configuration
DETAIL_PANEL_DELAY_MIN = 1.5  # seconds
DETAIL_PANEL_DELAY_MAX = 3.5  # seconds

# Fields to extract with fallback strategies
EXTRACTION_FIELDS = [
    'phone', 'address', 'category', 'website', 'rating', 'reviewsCount',
    'businessStatus', 'workingHours', 'plusCode', 'coordinates'
]


class GoogleMapsScraper(BaseScraper):
    name = "google-maps"
    browser_type = "chromium"
    timeout_s = 60
    max_retries = 2
    async def discover(self, ctx: ScrapeContext) -> List[Dict[str, Any]]:
        """Discover businesses with enforced 20-lead limit."""
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
            
            # Check for Google blocking first
            if await self._is_google_blocked(page):
                logger.warning("GOOGLE_BLOCKED: Detected CAPTCHA or unusual traffic page")
                return []
            
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
                    const pidMatch = href.match(/maps\\/place\\/([^/]+)/);
                    const placeId = pidMatch ? decodeURIComponent(pidMatch[1]) : '';
                    leads.push({ 
                        companyName: name, 
                        sourceUrl: href, 
                        placeId, 
                        source: 'google-maps', 
                        cardIndex: leads.length 
                    });
                }
                return leads;
                }"""
            )
            
            if not cards:
                logger.warning("No cards found for query: {}", search_query)
                return []
            
            # Enforce hard 20-lead limit
            effective_limit = min(ctx.max_results or MAX_LEADS_PER_SEARCH, MAX_LEADS_PER_SEARCH)
            cards_to_process = cards[:effective_limit]
            
            logger.info(
                "Found {} cards, processing {} (limit={})", 
                len(cards), 
                len(cards_to_process),
                effective_limit
            )
            # Extract detailed information for each business with rate limiting
            detailed_leads = []
            data_quality = DataQuality(
                fieldsAttempted=EXTRACTION_FIELDS,
                fieldsPopulated={field: 0 for field in EXTRACTION_FIELDS},
                fillRatePercent={field: 0.0 for field in EXTRACTION_FIELDS},
                totalLeads=len(cards_to_process),
                extractionWarnings=[]
            )
            
            for i, card in enumerate(cards_to_process):
                try:
                    # Rate limiting: randomized delay between businesses
                    if i > 0:
                        delay = random.uniform(DETAIL_PANEL_DELAY_MIN, DETAIL_PANEL_DELAY_MAX)
                        await asyncio.sleep(delay)
                    
                    # Extract with retry and fallback
                    detailed_lead = await self._extract_business_with_retry(page, card, i, data_quality)
                    if detailed_lead:
                        detailed_leads.append(detailed_lead)
                        logger.debug("Extracted details for: {}", detailed_lead.get('companyName', 'Unknown'))
                    
                    # Check for blocking after each extraction
                    if await self._is_google_blocked(page):
                        logger.warning(
                            "GOOGLE_BLOCKED: Stopping batch at {} of {} leads due to blocking", 
                            i + 1, 
                            len(cards_to_process)
                        )
                        break
                        
                except Exception as e:
                    logger.warning(
                        "Error extracting details for business {}: {} - {}", 
                        i, 
                        card.get('companyName', 'Unknown'), 
                        str(e)
                    )
                    # Keep basic info on error
                    detailed_leads.append(card)
            
            # Calculate and log data quality metrics
            self._calculate_data_quality_metrics(data_quality)
            self._log_data_quality_results(data_quality)
            
            # Store data quality for response
            ctx.metadata['dataQuality'] = data_quality.dict()
            
            return detailed_leads
            
        except Exception as exc:
            await self._capture_failure_artifacts(ctx, exc, page)
            logger.error("{} discovery failed | error={}", self.name, exc)
            return []
        finally:
            await browser_pool.release(page, self.name)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=3))
    async def _extract_business_with_retry(
        self, 
        page: Page, 
        card: Dict[str, Any], 
        index: int,
        data_quality: DataQuality
    ) -> Dict[str, Any]:
        """Extract business details with retry logic and fallback strategies."""
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
            
            # Check if we got an empty detail panel (retry trigger)
            panel_content = await page.evaluate(
                "() => document.querySelector('div[role=\"main\"]')?.textContent?.trim() || ''"
            )
            if not panel_content or len(panel_content) < 50:
                raise Exception("Empty or minimal detail panel detected")
            
            # Extract all details with resilient strategies
            details = {
                'companyName': card.get('companyName'),
                'sourceUrl': await self._get_current_maps_url(page),
                'placeId': card.get('placeId'),
                'source': 'google-maps'
            }
            
            # Extract each field with individual error handling and fallbacks
            extraction_results = await asyncio.gather(
                self._resilient_extract_category(page),
                self._resilient_extract_address_and_location(page),
                self._resilient_extract_contact_info(page),
                self._resilient_extract_rating_and_reviews(page),
                self._resilient_extract_business_status_and_hours(page),
                self._resilient_extract_additional_info(page),
                self._resilient_extract_coordinates(page),
                return_exceptions=True
            )
            
            # Merge results and track data quality
            for result in extraction_results:
                if isinstance(result, dict):
                    details.update(result)
                    # Track which fields were successfully populated
                    for field in EXTRACTION_FIELDS:
                        if field in result and result[field] is not None:
                            data_quality.fieldsPopulated[field] += 1
                elif isinstance(result, Exception):
                    logger.debug("Field extraction error: {}", str(result))
            
            return details
            
        except Exception as e:
            logger.warning("Failed to extract business details for {}: {}", card.get('companyName', 'Unknown'), str(e))
            # Capture failure artifacts for debugging if 2+ fields failed
            failed_fields = sum(1 for field in EXTRACTION_FIELDS if field not in details or details.get(field) is None)
            if failed_fields >= 2:
                await self._capture_detail_failure_artifacts(page, card, str(e))
            raise  # Re-raise to trigger retry
    async def _resilient_extract_category(self, page: Page) -> Dict[str, Any]:
        """Extract category with 3-layer fallback: selectors → text patterns."""
        result = {'category': None}
        
        try:
            # Layer 1: Primary CSS selectors
            for selector in DETAIL_CATEGORY[:3]:  # Use first 3 as primary
                try:
                    element = await page.query_selector(selector)
                    if element:
                        category = await element.inner_text()
                        if category and category.strip():
                            result['category'] = category.strip()
                            return result
                except Exception:
                    continue
            
            # Layer 2: Secondary CSS selectors
            for selector in DETAIL_CATEGORY[3:]:  # Remaining as secondary
                try:
                    element = await page.query_selector(selector)
                    if element:
                        category = await element.inner_text()
                        if category and category.strip():
                            result['category'] = category.strip()
                            return result
                except Exception:
                    continue
            
            # Layer 3: Text pattern fallback - scan visible text
            try:
                page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                # Look for common category patterns
                category_patterns = [
                    r'Category:?\s*([A-Za-z\s&]+)',
                    r'Business type:?\s*([A-Za-z\s&]+)',
                    r'Type:?\s*([A-Za-z\s&]+)',
                ]
                
                for pattern in category_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        category = match.group(1).strip()
                        if len(category) > 2 and len(category) < 50:
                            result['category'] = category
                            return result
            except Exception:
                pass
                
        except Exception as e:
            logger.debug("Category extraction failed: {}", str(e))
        
        return result

    async def _resilient_extract_address_and_location(self, page: Page) -> Dict[str, Any]:
        """Extract address with 3-layer fallback and component parsing."""
        result = {
            'address': None, 'area': None, 'city': None, 'state': None, 
            'country': None, 'pincode': None, 'postalCode': None
        }
        
        try:
            # Layer 1: Primary address selectors
            for selector in DETAIL_ADDRESS[:2]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        address_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if address_text and address_text.strip():
                            address = re.sub(r'^(Address: |Address )', '', address_text.strip())
                            components = parse_address_components(address)
                            result.update({
                                'address': address,
                                'area': components.get('area'),
                                'city': components.get('city'),
                                'state': components.get('state'),
                                'country': components.get('country'),
                                'pincode': components.get('pincode'),
                                'postalCode': components.get('pincode'),
                            })
                            return result
                except Exception:
                    continue
            
            # Layer 2: Secondary address selectors
            for selector in DETAIL_ADDRESS[2:]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        address_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if address_text and address_text.strip():
                            address = re.sub(r'^(Address: |Address )', '', address_text.strip())
                            components = parse_address_components(address)
                            result.update({
                                'address': address,
                                'area': components.get('area'),
                                'city': components.get('city'), 
                                'state': components.get('state'),
                                'country': components.get('country'),
                                'pincode': components.get('pincode'),
                                'postalCode': components.get('pincode'),
                            })
                            return result
                except Exception:
                    continue
            
            # Layer 3: Text pattern fallback
            try:
                page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                address_patterns = [
                    r'Address:?\s*([^\n]+(?:\n[^\n]+){0,2})',  # Multi-line address
                    r'Located at:?\s*([^\n]+)',
                    r'Find us at:?\s*([^\n]+)',
                ]
                
                for pattern in address_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        address = match.group(1).strip()
                        if len(address) > 10:
                            components = parse_address_components(address)
                            result.update({
                                'address': address,
                                'area': components.get('area'),
                                'city': components.get('city'),
                                'state': components.get('state'),
                                'country': components.get('country'),
                                'pincode': components.get('pincode'),
                                'postalCode': components.get('pincode'),
                            })
                            return result
            except Exception:
                pass
                
        except Exception as e:
            logger.debug("Address extraction failed: {}", str(e))
        
        return result
    async def _resilient_extract_contact_info(self, page: Page) -> Dict[str, Any]:
        """Extract phone and website with 3-layer fallback."""
        result = {'phone': None, 'website': None}
        
        # Extract phone with resilient strategy
        try:
            # Layer 1: Primary phone selectors
            for selector in DETAIL_PHONE[:3]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        phone_text = await element.get_attribute('aria-label') or await element.inner_text()
                        if phone_text:
                            phone_match = re.search(r'[\+]?[\d\s\-\(\)\.]+', phone_text)
                            if phone_match:
                                result['phone'] = phone_match.group().strip()
                                break
                except Exception:
                    continue
            
            # Layer 2: Secondary phone selectors if not found
            if not result['phone']:
                for selector in DETAIL_PHONE[3:]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            phone_text = await element.get_attribute('aria-label') or await element.inner_text()
                            if phone_text:
                                phone_match = re.search(r'[\+]?[\d\s\-\(\)\.]+', phone_text)
                                if phone_match:
                                    result['phone'] = phone_match.group().strip()
                                    break
                    except Exception:
                        continue
            
            # Layer 3: Text pattern fallback for phone
            if not result['phone']:
                try:
                    page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                    for pattern in PHONE_PATTERNS:
                        match = re.search(pattern, page_text)
                        if match:
                            result['phone'] = match.group().strip()
                            break
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug("Phone extraction failed: {}", str(e))
        
        # Extract website with resilient strategy
        try:
            # Layer 1: Primary website selectors
            for selector in DETAIL_WEBSITE[:3]:
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
            
            # Layer 2: Secondary website selectors if not found
            if not result['website']:
                for selector in DETAIL_WEBSITE[3:]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            href = await element.get_attribute('href')
                            if href:
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
            
            # Layer 3: Text pattern fallback for website
            if not result['website']:
                try:
                    page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                    website_patterns = [
                        r'(https?://[^\s]+)',
                        r'(www\.[^\s]+\.[a-z]{2,})',
                        r'Website:?\s*(https?://[^\s]+)',
                    ]
                    for pattern in website_patterns:
                        match = re.search(pattern, page_text, re.IGNORECASE)
                        if match:
                            result['website'] = match.group(1)
                            break
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug("Website extraction failed: {}", str(e))
            
        return result

    async def _resilient_extract_rating_and_reviews(self, page: Page) -> Dict[str, Any]:
        """Extract rating and review count with 3-layer fallback."""
        result = {'rating': None, 'reviewsCount': None}
        
        try:
            # Layer 1: Primary rating selectors
            for selector in DETAIL_RATING[:2]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        aria_label = await element.get_attribute('aria-label')
                        if aria_label:
                            rating_match = re.search(r'(\d+\.?\d*)\s*stars?', aria_label)
                            review_match = re.search(r'(\d+)\s*reviews?', aria_label, re.IGNORECASE)
                            
                            if rating_match:
                                result['rating'] = float(rating_match.group(1))
                            if review_match:
                                result['reviewsCount'] = int(review_match.group(1))
                            
                            if result['rating'] or result['reviewsCount']:
                                return result
                except Exception:
                    continue
            
            # Layer 2: Secondary rating selectors
            for selector in DETAIL_RATING[2:]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        aria_label = await element.get_attribute('aria-label')
                        if aria_label:
                            rating_match = re.search(r'(\d+\.?\d*)\s*stars?', aria_label)
                            review_match = re.search(r'(\d+)\s*reviews?', aria_label, re.IGNORECASE)
                            
                            if rating_match:
                                result['rating'] = float(rating_match.group(1))
                            if review_match:
                                result['reviewsCount'] = int(review_match.group(1))
                                
                            if result['rating'] or result['reviewsCount']:
                                return result
                except Exception:
                    continue
            
            # Layer 3: Text pattern fallback
            try:
                page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                
                for pattern in RATING_PATTERNS:
                    match = re.search(pattern, page_text)
                    if match:
                        result['rating'] = float(match.group(1))
                        break
                
                for pattern in REVIEWS_PATTERNS:
                    match = re.search(pattern, page_text, re.IGNORECASE)
                    if match:
                        result['reviewsCount'] = int(match.group(1).replace(',', ''))
                        break
            except Exception:
                pass
                
        except Exception as e:
            logger.debug("Rating/reviews extraction failed: {}", str(e))
        
        return result
    async def _resilient_extract_business_status_and_hours(self, page: Page) -> Dict[str, Any]:
        """Extract business status and working hours with 3-layer fallback."""
        result = {'businessStatus': None, 'workingHours': None}
        
        try:
            # Layer 1: Primary business status selectors
            for selector in DETAIL_BUSINESS_STATUS[:3]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        status_text = await element.inner_text()
                        if status_text and any(word in status_text.lower() for word in ['open', 'closed', 'closes', 'opens']):
                            result['businessStatus'] = status_text.strip()
                            break
                except Exception:
                    continue
            
            # Layer 2: Secondary business status selectors
            if not result['businessStatus']:
                for selector in DETAIL_BUSINESS_STATUS[3:]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            status_text = await element.inner_text()
                            if status_text and any(word in status_text.lower() for word in ['open', 'closed', 'closes', 'opens']):
                                result['businessStatus'] = status_text.strip()
                                break
                    except Exception:
                        continue
            
            # Layer 3: Text pattern fallback for business status
            if not result['businessStatus']:
                try:
                    page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                    for pattern in BUSINESS_STATUS_PATTERNS:
                        match = re.search(pattern, page_text, re.IGNORECASE)
                        if match:
                            result['businessStatus'] = match.group().strip()
                            break
                except Exception:
                    pass
            
            # Extract working hours
            # Layer 1: Primary hours selectors
            for selector in DETAIL_WORKING_HOURS[:2]:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        hours_text = await element.inner_text()
                        if hours_text and len(hours_text.strip()) > 5:
                            result['workingHours'] = hours_text.strip()
                            break
                except Exception:
                    continue
            
            # Layer 2: Secondary hours selectors
            if not result['workingHours']:
                for selector in DETAIL_WORKING_HOURS[2:]:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            hours_text = await element.inner_text()
                            if hours_text and len(hours_text.strip()) > 5:
                                result['workingHours'] = hours_text.strip()
                                break
                    except Exception:
                        continue
            
            # Layer 3: Text pattern fallback for hours
            if not result['workingHours']:
                try:
                    page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                    hours_patterns = [
                        r'Hours?:?\s*([^\n]+(?:\n[^\n]+){0,6})',  # Multi-line hours
                        r'Open:?\s*([^\n]+)',
                        r'Timing:?\s*([^\n]+)',
                    ]
                    for pattern in hours_patterns:
                        match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                        if match:
                            hours = match.group(1).strip()
                            if len(hours) > 5:
                                result['workingHours'] = hours
                                break
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug("Business status/hours extraction failed: {}", str(e))
        
        return result

    async def _resilient_extract_additional_info(self, page: Page) -> Dict[str, Any]:
        """Extract plus code and other additional info with fallbacks."""
        result = {
            'plusCode': None,
            'ownerClaimed': None,
            'totalPhotos': None,
            'serviceOptions': None,
        }
        
        try:
            # Extract plus code
            for selector in DETAIL_PLUS_CODE:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        plus_code_text = await element.inner_text()
                        if plus_code_text and re.match(PLUS_CODE_PATTERN, plus_code_text.replace(' ', '')):
                            result['plusCode'] = plus_code_text.strip()
                            break
                except Exception:
                    continue
            
            # Text pattern fallback for plus code
            if not result['plusCode']:
                try:
                    page_text = await page.evaluate("() => document.querySelector('div[role=\"main\"]')?.innerText || ''")
                    match = re.search(PLUS_CODE_PATTERN, page_text)
                    if match:
                        result['plusCode'] = match.group(1)
                except Exception:
                    pass
            
            # Check if owner claimed
            try:
                claim_button = await page.query_selector('button[aria-label*="Claim this business"]')
                result['ownerClaimed'] = claim_button is None
            except Exception:
                pass
            
            # Extract total photos count
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
            
            # Extract service options
            for selector in DETAIL_SERVICE_OPTIONS:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        service_text = await element.inner_text()
                        if service_text and len(service_text.strip()) > 3:
                            if any(sep in service_text for sep in [',', '•', '\n']):
                                services = [s.strip() for s in re.split(r'[,•\n]', service_text) if s.strip()]
                                result['serviceOptions'] = services
                            else:
                                result['serviceOptions'] = [service_text.strip()]
                            break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.debug("Additional info extraction failed: {}", str(e))
            
        return result

    async def _resilient_extract_coordinates(self, page: Page) -> Dict[str, Any]:
        """Extract latitude and longitude from URL."""
        try:
            current_url = page.url
            lat, lng = extract_coordinates_from_url(current_url)
            return {
                'latitude': lat,
                'longitude': lng
            }
        except Exception as e:
            logger.debug("Coordinates extraction failed: {}", str(e))
            return {'latitude': None, 'longitude': None}
    async def _is_google_blocked(self, page: Page) -> bool:
        """Check if Google has blocked our requests with CAPTCHA or traffic warning."""
        try:
            page_text = await page.evaluate("() => document.body?.innerText?.toLowerCase() || ''")
            for pattern in GOOGLE_BLOCKING_PATTERNS:
                if re.search(pattern, page_text, re.IGNORECASE):
                    return True
            return False
        except Exception:
            return False

    async def _get_current_maps_url(self, page: Page) -> str:
        """Get the current Google Maps URL."""
        try:
            return page.url
        except Exception:
            return ""

    def _calculate_data_quality_metrics(self, data_quality: DataQuality) -> None:
        """Calculate fill rate percentages and detect quality issues."""
        if data_quality.totalLeads == 0:
            return
            
        for field in EXTRACTION_FIELDS:
            populated_count = data_quality.fieldsPopulated.get(field, 0)
            fill_rate = populated_count / data_quality.totalLeads
            data_quality.fillRatePercent[field] = round(fill_rate, 3)
            
            # Check against thresholds
            threshold = FILL_RATE_THRESHOLDS.get(field)
            if threshold and fill_rate < threshold:
                warning = f"{field} fill-rate {fill_rate:.1%} below threshold {threshold:.1%}"
                data_quality.extractionWarnings.append(warning)

    def _log_data_quality_results(self, data_quality: DataQuality) -> None:
        """Log data quality metrics for visibility."""
        fill_rates = []
        for field in EXTRACTION_FIELDS:
            count = data_quality.fieldsPopulated.get(field, 0)
            total = data_quality.totalLeads
            percentage = data_quality.fillRatePercent.get(field, 0) * 100
            fill_rates.append(f"{field}: {count}/{total} ({percentage:.0f}%)")
        
        logger.info("Data Quality | {}", ", ".join(fill_rates))
        
        # Log warnings for low fill rates
        for warning in data_quality.extractionWarnings:
            logger.warning("Data Quality Warning | {}", warning)

    async def _capture_detail_failure_artifacts(
        self, 
        page: Page, 
        card: Dict[str, Any], 
        error_msg: str
    ) -> None:
        """Capture failure artifacts for business detail extraction failures."""
        try:
            business_name = card.get('companyName', 'unknown').replace(' ', '_')[:50]
            timestamp = asyncio.get_event_loop().time()
            
            # Screenshot
            screenshot_path = self.debug_dir / f"detail_failure_{business_name}_{timestamp}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Page HTML
            html_path = self.debug_dir / f"detail_failure_{business_name}_{timestamp}.html"
            content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Error details
            error_path = self.debug_dir / f"detail_failure_{business_name}_{timestamp}.txt"
            with open(error_path, 'w', encoding='utf-8') as f:
                f.write(f"Business: {card}\n")
                f.write(f"Error: {error_msg}\n")
                f.write(f"URL: {page.url}\n")
                f.write(f"Time: {timestamp}\n")
            
            logger.debug("Captured failure artifacts for {}: {}", business_name, self.debug_dir)
        except Exception as e:
            logger.debug("Failed to capture debug artifacts: {}", str(e))
    # Inherit remaining methods from base implementation with minor modifications
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
            
            # Include data quality in response
            data_quality = ctx.metadata.get('dataQuality')
            
            return {
                "success": bool(enriched),
                "source": self.name,
                "total_extracted": len(enriched),
                "total_stored": len(enriched),
                "total_duplicates": 0,
                "leads": enriched,
                "dataQuality": data_quality
            }
        except Exception as exc:
            logger.error("{} scrape failed | error={}", self.name, exc)
            return {
                "success": False, 
                "source": self.name, 
                "total_extracted": 0, 
                "total_stored": 0, 
                "total_duplicates": 0, 
                "leads": [], 
                "error": str(exc)
            }