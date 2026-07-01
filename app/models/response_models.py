"""Response models for the AI Analysis Service."""

from typing import List, Optional

from pydantic import BaseModel, Field


class WebsiteAnalysis(BaseModel):
    """Website analysis result."""
    
    sslEnabled: Optional[bool] = None
    responseTime: Optional[int] = None
    metaTitle: Optional[str] = None
    metaDescription: Optional[str] = None
    hasContactPage: Optional[bool] = None
    hasSocialLinks: Optional[bool] = None
    websiteStatus: Optional[str] = None
    rating: Optional[float] = None
    reviewsCount: Optional[int] = None


class BusinessOpportunity(BaseModel):
    """Business opportunity suggestion."""
    
    type: str = Field(..., description="Opportunity type")
    description: str = Field(..., description="Opportunity description")
    priority: str = Field(default="medium", description="Priority level")


class LeadAnalysisResult(BaseModel):
    """Result of lead analysis."""
    
    leadScore: int = Field(..., ge=0, le=100, description="Final lead score (0-100)")
    qualificationLevel: str = Field(..., description="Qualification level")
    websiteWeaknesses: List[str] = Field(default_factory=list, description="List of website weaknesses")
    businessOpportunities: List[str] = Field(default_factory=list, description="List of business opportunities")
    summary: str = Field(..., description="Professional summary of analysis")
    analysisTimestamp: str = Field(..., description="Timestamp of analysis")
    companyName: Optional[str] = None
    website: Optional[str] = None
    category: Optional[str] = None


class BulkAnalysisResult(BaseModel):
    """Result of bulk analysis."""
    
    totalProcessed: int = Field(..., description="Total number of leads processed")
    successful: int = Field(..., description="Number of successful analyses")
    failed: int = Field(..., description="Number of failed analyses")
    results: List[LeadAnalysisResult] = Field(default_factory=list, description="Analysis results")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(default="healthy", description="Service status")
    service: str = Field(default="lead-finder-ai-analysis", description="Service name")
    version: str = Field(default="1.0.0", description="Service version")
    uptime: Optional[int] = None
    timestamp: str


class ErrorResponse(BaseModel):
    """Error response."""
    
    success: bool = Field(default=False)
    message: str = Field(..., description="Error message")
    error: Optional[str] = None
    details: Optional[dict] = None
