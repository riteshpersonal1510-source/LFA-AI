#!/usr/bin/env python3
"""
Test script for the enhanced Google Maps scraper to verify:
1. 20-lead limit enforcement
2. Data quality metrics
3. Resilient extraction with fallbacks
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from scraper_service.scrapers.google_maps.scraper import GoogleMapsScraper
from scraper_service.scrapers.base import ScrapeContext


async def test_enhanced_scraper():
    """Test the enhanced Google Maps scraper with a real search."""
    print("🚀 Testing Enhanced Google Maps Scraper")
    print("=" * 50)
    
    scraper = GoogleMapsScraper()
    
    # Test context - searching for restaurants in New York
    ctx = ScrapeContext(
        keyword="restaurant",
        business_type="restaurant",
        location="New York",
        city="New York",
        state="NY",
        country="USA",
        max_results=25,  # Requesting more than 20 to test limit
        session_id="test_session_001"
    )
    
    print(f"🔍 Searching for: {ctx.keyword}")
    print(f"📍 Location: {ctx.location}")
    print(f"📊 Requested results: {ctx.max_results}")
    print(f"🎯 Expected limit: 20 (MAX_LEADS_PER_SEARCH)")
    print()
    
    try:
        # Run the scraper
        result = await scraper.scrape(ctx)
        
        print("✅ SCRAPE COMPLETED")
        print("=" * 50)
        print(f"🏆 Success: {result['success']}")
        print(f"📈 Total Extracted: {result['total_extracted']}")
        print(f"💾 Total Stored: {result['total_stored']}")
        
        if result.get('dataQuality'):
            dq = result['dataQuality']
            print()
            print("📊 DATA QUALITY METRICS")
            print("-" * 30)
            print(f"Total Leads Processed: {dq['totalLeads']}")
            print(f"Fields Attempted: {', '.join(dq['fieldsAttempted'])}")
            print()
            print("Fill Rates:")
            for field, rate in dq['fillRatePercent'].items():
                count = dq['fieldsPopulated'].get(field, 0)
                print(f"  {field:15}: {count:2}/{dq['totalLeads']} ({rate*100:5.1f}%)")
            
            if dq['extractionWarnings']:
                print()
                print("⚠️  EXTRACTION WARNINGS:")
                for warning in dq['extractionWarnings']:
                    print(f"  - {warning}")
        
        print()
        print("📋 SAMPLE LEADS (first 3):")
        print("-" * 30)
        for i, lead in enumerate(result['leads'][:3]):
            print(f"\nLead {i+1}:")
            print(f"  Company: {lead.get('companyName', 'N/A')}")
            print(f"  Phone: {lead.get('phone', 'N/A')}")
            print(f"  Website: {lead.get('website', 'N/A')}")
            print(f"  Address: {lead.get('address', 'N/A')}")
            print(f"  Category: {lead.get('category', 'N/A')}")
            print(f"  Rating: {lead.get('rating', 'N/A')}")
            print(f"  Reviews: {lead.get('reviewsCount', 'N/A')}")
        
        print()
        print("🎯 LIMIT ENFORCEMENT TEST:")
        print(f"  Requested: {ctx.max_results} leads")
        print(f"  Received: {result['total_extracted']} leads")
        print(f"  Limit Enforced: {'✅ YES' if result['total_extracted'] <= 20 else '❌ NO'}")
        
        return result
        
    except Exception as e:
        print(f"❌ SCRAPER FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_enhanced_scraper())
    
    if result and result['success']:
        print()
        print("🎉 TEST PASSED - Enhanced scraper working correctly!")
        sys.exit(0)
    else:
        print()
        print("💥 TEST FAILED - Check errors above")
        sys.exit(1)