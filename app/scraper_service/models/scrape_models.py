"""Request and response models for the scraper API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    keyword: str = Field(..., min_length=1, description="Business type to search for")
    location: Optional[str] = Field(None, description="Generic location string")
    state: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None
    country: Optional[str] = Field(None, description="Country code or name")
    sources: List[str] = Field(
        default=["google-maps", "justdial", "indiamart"],
        description="Sources to scrape from",
    )
    limit: int = Field(default=0, ge=0, description="Max leads per source, 0=unlimited")
    businessType: Optional[str] = None
    sessionId: Optional[str] = None
    semanticExpansion: bool = False
    maxResults: Optional[int] = None
    resumeSessionId: Optional[str] = None


class SourceResult(BaseModel):
    source: str
    totalExtracted: int = 0
    totalStored: int = 0
    totalDuplicates: int = 0
    success: bool = False
    error: Optional[str] = None


class ScrapedLead(BaseModel):
    companyName: str
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    rating: Optional[float] = None
    reviewsCount: Optional[int] = None
    source: str
    sourceUrl: Optional[str] = None
    placeId: Optional[str] = None
    href: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    area: Optional[str] = None
    country: Optional[str] = None
    businessType: Optional[str] = None
    fullSearchQuery: Optional[str] = None
    searchedKeyword: Optional[str] = None
    searchedLocation: Optional[str] = None
    searchedCity: Optional[str] = None
    searchedState: Optional[str] = None
    searchedArea: Optional[str] = None
    searchedCountry: Optional[str] = None
    searchedBusinessType: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = None
    postalCode: Optional[str] = None
    streetAddress: Optional[str] = None
    workingHours: Optional[str] = None
    businessStatus: Optional[str] = None
    plusCode: Optional[str] = None
    secondaryCategories: Optional[List[str]] = None
    serviceOptions: Optional[List[str]] = None
    ownerClaimed: Optional[bool] = None
    totalPhotos: Optional[int] = None
    searchRank: Optional[int] = None
    relevanceScore: Optional[int] = None
    leadScore: Optional[int] = None
    semanticKeyword: Optional[str] = None
    extraData: Optional[Dict[str, Any]] = None


class ScrapeResponse(BaseModel):
    success: bool
    message: str
    sessionId: Optional[str] = None
    totalExtracted: int = 0
    totalStored: int = 0
    totalDuplicates: int = 0
    sourceResults: List[SourceResult] = []
    leads: List[ScrapedLead] = []
    errors: Optional[List[Dict[str, str]]] = None


class ProgressData(BaseModel):
    sessionId: str
    status: str  # running | completed | failed
    totalFound: int = 0
    totalScraped: int = 0
    totalSaved: int = 0
    totalDuplicates: int = 0
    totalRejected: int = 0
    currentSource: Optional[str] = None
    currentBusiness: Optional[str] = None
    errors: List[str] = []
    startedAt: Optional[str] = None
    updatedAt: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    playwright: str
    mongodb: str
    uptime: float
    timestamp: str
