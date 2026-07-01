"""Analysis routes for the AI Analysis Service."""

import time
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..config.settings import Settings, get_settings
from ..models.request_models import LeadAnalysisRequest, BulkAnalysisRequest
from ..models.response_models import (
    BulkAnalysisResult,
    LeadAnalysisResult,
    ErrorResponse,
)
from ..services.scoring_engine import ScoringEngine
from ..services.qualification_engine import QualificationEngine
from ..services.summary_engine import SummaryEngine
from ..services.business_opportunity_engine import BusinessOpportunityEngine
from ..services.website_analysis_engine import WebsiteAnalysisEngine

router = APIRouter()


class SingleAnalysisResult(BaseModel):
    """Result of single lead analysis."""
    
    leadScore: int
    qualificationLevel: str
    websiteWeaknesses: List[str]
    businessOpportunities: List[str]
    summary: str
    analysisTimestamp: str
    companyName: str
    website: str = None
    category: str = None


@router.post("/analyze-lead", response_model=SingleAnalysisResult)
async def analyze_single_lead(
    request: LeadAnalysisRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Analyze a single lead for website quality and qualification.
    
    Args:
        request: Lead analysis request
        settings: Application settings
        
    Returns:
        Analysis result with score, qualification, and recommendations
    """
    try:
        start_time = time.time()
        
        # Perform business analysis
        analysis_result = QualificationEngine.analyze_business(
            website_status=request.websiteStatus,
            ssl_enabled=request.sslEnabled,
            meta_title=request.metaTitle,
            meta_description=request.metaDescription,
            has_contact_page=request.hasContactPage,
            has_social_links=request.hasSocialLinks,
            response_time=request.responseTime,
            reviews_count=request.reviewsCount,
        )
        
        # Get summary
        summary = SummaryEngine.generate_summary(
            qualification_level=analysis_result["qualification"],
            weaknesses=analysis_result["weaknesses"],
            opportunities=analysis_result["opportunities"],
            website_status=request.websiteStatus,
            score=analysis_result["score"],
        )
        
        # Get website status
        website_status = WebsiteAnalysisEngine.analyze_website_status(
            website_status=request.websiteStatus,
            ssl_enabled=request.sslEnabled,
            has_contact_page=request.hasContactPage,
            has_social_links=request.hasSocialLinks,
            response_time=request.responseTime,
        )
        
        return {
            "leadScore": analysis_result["score"],
            "qualificationLevel": analysis_result["qualification"],
            "websiteWeaknesses": analysis_result["weaknesses"],
            "businessOpportunities": analysis_result["opportunities"],
            "summary": summary,
            "analysisTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "companyName": request.companyName,
            "website": request.website,
            "category": request.category,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.post("/bulk-analyze", response_model=BulkAnalysisResult)
async def analyze_bulk_leads(
    request: BulkAnalysisRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Analyze multiple leads in bulk.
    
    Args:
        request: Bulk analysis request
        settings: Application settings
        
    Returns:
        Bulk analysis results
    """
    try:
        start_time = time.time()
        results = []
        failed = 0
        successful = 0
        
        # Process leads in batches
        batch_size = min(request.batchSize or 10, 50)
        
        for i in range(0, len(request.leads), batch_size):
            batch = request.leads[i:i + batch_size]
            
            for lead in batch:
                try:
                    # Perform analysis
                    analysis_result = QualificationEngine.analyze_business(
                        website_status=lead.websiteStatus,
                        ssl_enabled=lead.sslEnabled,
                        meta_title=lead.metaTitle,
                        meta_description=lead.metaDescription,
                        has_contact_page=lead.hasContactPage,
                        has_social_links=lead.hasSocialLinks,
                        response_time=lead.responseTime,
                        reviews_count=lead.reviewsCount,
                    )
                    
                    # Get summary
                    summary = SummaryEngine.generate_summary(
                        qualification_level=analysis_result["qualification"],
                        weaknesses=analysis_result["weaknesses"],
                        opportunities=analysis_result["opportunities"],
                        website_status=lead.websiteStatus,
                        score=analysis_result["score"],
                    )
                    
                    results.append({
                        "leadScore": analysis_result["score"],
                        "qualificationLevel": analysis_result["qualification"],
                        "websiteWeaknesses": analysis_result["weaknesses"],
                        "businessOpportunities": analysis_result["opportunities"],
                        "summary": summary,
                        "analysisTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "companyName": lead.companyName,
                        "website": lead.website,
                        "category": lead.category,
                    })
                    
                    successful += 1
                    
                except Exception as e:
                    failed += 1
                    continue
        
        return {
            "totalProcessed": len(request.leads),
            "successful": successful,
            "failed": failed,
            "results": results,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk analysis failed: {str(e)}",
        )


@router.post("/score-only")
async def calculate_score_only(
    request: LeadAnalysisRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Calculate only the lead score without full analysis.
    
    Args:
        request: Lead analysis request
        settings: Application settings
        
    Returns:
        Score calculation result
    """
    try:
        score = ScoringEngine.calculate_score(
            website_status=request.websiteStatus,
            ssl_enabled=request.sslEnabled,
            meta_title=request.metaTitle,
            meta_description=request.metaDescription,
            has_contact_page=request.hasContactPage,
            has_social_links=request.hasSocialLinks,
            response_time=request.responseTime,
            reviews_count=request.reviewsCount,
        )
        
        qualification = ScoringEngine.get_qualification(score)
        
        return {
            "leadScore": score,
            "qualificationLevel": qualification,
            "analysisTimestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Score calculation failed: {str(e)}",
        )
