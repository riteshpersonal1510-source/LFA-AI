"""Request models for the AI Analysis Service."""

from typing import List, Optional

from pydantic import BaseModel, Field


class LeadAnalysisRequest(BaseModel):
    """Request model for single lead analysis."""
    
    companyName: str = Field(..., min_length=1, description="Company name")
    website: Optional[str] = Field(None, description="Company website URL")
    category: Optional[str] = Field(None, description="Business category")
    websiteStatus: Optional[str] = Field(None, description="Website status")
    sslEnabled: Optional[bool] = Field(None, description="SSL enabled")
    responseTime: Optional[int] = Field(None, description="Response time in ms")
    metaTitle: Optional[str] = Field(None, description="Meta title")
    metaDescription: Optional[str] = Field(None, description="Meta description")
    hasContactPage: Optional[bool] = Field(None, description="Has contact page")
    hasSocialLinks: Optional[bool] = Field(None, description="Has social links")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Business rating")
    reviewsCount: Optional[int] = Field(None, ge=0, description="Number of reviews")
    leadScore: Optional[int] = Field(None, ge=0, le=100, description="Initial lead score")


class BulkAnalysisRequest(BaseModel):
    """Request model for bulk analysis."""
    
    leads: List[LeadAnalysisRequest] = Field(..., min_length=1, max_length=1000, description="List of leads to analyze")
    batchSize: Optional[int] = Field(default=10, ge=1, le=100, description="Batch size for processing")


class AnalysisRequest(BaseModel):
    """Request model for analysis endpoint."""
    
    companyName: str = Field(..., min_length=1)
    website: Optional[str] = None
    category: Optional[str] = None
    websiteStatus: Optional[str] = None
    sslEnabled: Optional[bool] = None
    responseTime: Optional[int] = None
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    hasContactPage: Optional[bool] = None
    hasSocialLinks: Optional[bool] = None
    rating: Optional[float] = None
    reviewsCount: Optional[int] = None
    leadScore: Optional[int] = None


class BulkAnalysisRequestSimple(BaseModel):
    """Simplified bulk analysis request."""
    
    leads: List[AnalysisRequest] = Field(..., min_length=1, max_length=1000)
