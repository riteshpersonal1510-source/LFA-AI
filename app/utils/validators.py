"""Request validators for the AI Analysis Service."""

import re
from typing import Optional

from ..models.request_models import LeadAnalysisRequest, BulkAnalysisRequest


def validate_url(url: Optional[str]) -> bool:
    """Validate URL format."""
    if not url:
        return True
    
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$',
        re.IGNORECASE,
    )
    
    return bool(url_pattern.match(url))


def validate_lead_score(score: int) -> bool:
    """Validate lead score is within range."""
    return 0 <= score <= 100


def validate_response_time(response_time: Optional[int]) -> bool:
    """Validate response time is reasonable."""
    if response_time is None:
        return True
    
    return 0 <= response_time <= 60000  # Max 60 seconds


def validate_review_count(count: Optional[int]) -> bool:
    """Validate review count is reasonable."""
    if count is None:
        return True
    
    return count >= 0


def validate_analysis_request(request: LeadAnalysisRequest) -> bool:
    """Validate a single analysis request."""
    if not request.companyName:
        raise ValueError("Company name is required")
    
    if request.website and not validate_url(request.website):
        raise ValueError("Invalid website URL format")
    
    if request.leadScore is not None and not validate_lead_score(request.leadScore):
        raise ValueError("Lead score must be between 0 and 100")
    
    if request.responseTime is not None and not validate_response_time(request.responseTime):
        raise ValueError("Response time must be between 0 and 60000 milliseconds")
    
    if request.reviewsCount is not None and not validate_review_count(request.reviewsCount):
        raise ValueError("Reviews count must be non-negative")
    
    return True


def validate_bulk_request(request: BulkAnalysisRequest) -> bool:
    """Validate a bulk analysis request."""
    if not request.leads or len(request.leads) == 0:
        raise ValueError("At least one lead is required for bulk analysis")
    
    if len(request.leads) > 1000:
        raise ValueError("Maximum 1000 leads allowed in bulk request")
    
    for lead in request.leads:
        validate_analysis_request(lead)
    
    return True
