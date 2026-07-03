import asyncio
import os
import sys

# Add ai-service to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scraper_service.scrapers.google_maps.scraper import GoogleMapsScraper
from app.scraper_service.scrapers.justdial.scraper import JustDialScraper
from app.scraper_service.scrapers.indiamart.scraper import IndiaMartScraper
from app.scraper_service.browser.browser_pool import browser_pool

async def test_scraper(ScraperClass, keyword, location):
    print(f"\n--- Testing {ScraperClass.name} ---")
    scraper = ScraperClass()
    
    def on_lead(lead):
        print(f"[{ScraperClass.name}] 🟢 Streamed Lead: {lead.get('companyName')} | {lead.get('phone')} | {lead.get('sourceUrl')}")
        
    def on_progress(prog):
        print(f"[{ScraperClass.name}] 🔄 Progress: {prog}")
        
    try:
        result = await scraper.scrape(
            keyword=keyword,
            location=location,
            limit=3,
            on_lead=on_lead,
            on_progress=on_progress
        )
        print(f"[{ScraperClass.name}] ✅ Final Result: success={result.get('success')} extracted={result.get('total_extracted')}")
    except Exception as e:
        print(f"[{ScraperClass.name}] ❌ Error: {e}")

async def main():
    await browser_pool.start()
    
    # Test Google Maps
    await test_scraper(GoogleMapsScraper, keyword="Plumbers", location="New York")
    
    # Test JustDial
    await test_scraper(JustDialScraper, keyword="Plumbers", location="Mumbai")
    
    # Test IndiaMart
    await test_scraper(IndiaMartScraper, keyword="Plumbing Pipes", location="Delhi")
    
    await browser_pool.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
