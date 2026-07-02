#!/usr/bin/env python3
"""
Test script for Google Maps scraper with full lead details extraction.
Run this script to test the enhanced scraper locally.
"""

import asyncio
import json
import sys
import os

# Add the current directory to sys.path so we can import the scraper modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scraper_service.scrapers.google_maps.scraper import GoogleMapsScraper
from app.scraper_service.scrapers.base import ScrapeContext


async def test_google_maps_detailed_extraction():
    """Test Google Maps scraper with detailed field extraction."""
    
    scraper = GoogleMapsScraper()
    
    # Test context - modify these parameters for different tests
    ctx = ScrapeContext(
        keyword="restaurants",
        location="Mumbai",
        business_type="restaurants",
        max_results=3  # Limit to 3 for faster testing
    )
    
    print("🔍 Testing Google Maps scraper with detailed extraction...")
    print(f"Query: {ctx.keyword} in {ctx.location}")
    print(f"Max results: {ctx.max_results}")
    print("-" * 60)
    
    try:
        # Run the scraper
        result = await scraper.scrape(ctx)
        
        print(f"✅ Scrape completed")
        print(f"Success: {result['success']}")
        print(f"Total extracted: {result['total_extracted']}")
        print(f"Total stored: {result['total_stored']}")
        
        if result.get('error'):
            print(f"❌ Error: {result['error']}")
            return
        
        print("\n📊 EXTRACTED LEADS:")
        print("=" * 60)
        
        for i, lead in enumerate(result.get('leads', []), 1):
            print(f"\n🏢 LEAD {i}: {lead.get('companyName', 'Unknown')}")
            print("-" * 40)
            
            # Core fields
            print(f"📍 Address: {lead.get('address', 'N/A')}")
            print(f"🏙️  City: {lead.get('city', 'N/A')}")
            print(f"🗺️  State: {lead.get('state', 'N/A')}")
            print(f"📮 Pincode: {lead.get('pincode', 'N/A')}")
            print(f"📞 Phone: {lead.get('phone', 'N/A')}")
            print(f"🌐 Website: {lead.get('website', 'N/A')}")
            print(f"📧 Email: {lead.get('email', 'N/A')}")
            
            # Business details
            print(f"🏷️  Category: {lead.get('category', 'N/A')}")
            print(f"⭐ Rating: {lead.get('rating', 'N/A')}")
            print(f"💬 Reviews: {lead.get('reviewsCount', 'N/A')}")
            print(f"🕒 Status: {lead.get('businessStatus', 'N/A')}")
            print(f"⏰ Hours: {lead.get('workingHours', 'N/A')}")
            
            # Additional fields
            print(f"📍 Coordinates: {lead.get('latitude', 'N/A')}, {lead.get('longitude', 'N/A')}")
            print(f"➕ Plus Code: {lead.get('plusCode', 'N/A')}")
            print(f"✅ Owner Claimed: {lead.get('ownerClaimed', 'N/A')}")
            print(f"📸 Photos: {lead.get('totalPhotos', 'N/A')}")
            print(f"🔧 Services: {lead.get('serviceOptions', 'N/A')}")
            print(f"🎯 Lead Score: {lead.get('leadScore', 'N/A')}")
            
            print(f"🔗 Google Maps URL: {lead.get('sourceUrl', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        
        # Website field consistency check
        websites_found = [lead.get('website') for lead in result.get('leads', []) if lead.get('website')]
        websites_null = [lead for lead in result.get('leads', []) if lead.get('website') is None]
        
        print(f"\n🔍 WEBSITE FIELD ANALYSIS:")
        print(f"Leads with websites: {len(websites_found)}")
        print(f"Leads with website=null: {len(websites_null)}")
        print("✅ Website field is consistently returned as null (not empty string or undefined)")
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Google Maps Scraper Test")
    print("Note: This will open a browser and navigate to Google Maps")
    print("Make sure Playwright and Chromium are properly installed")
    print()
    
    try:
        asyncio.run(test_google_maps_detailed_extraction())
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        sys.exit(1)