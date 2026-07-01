"""Models package for the AI Analysis Service."""

from .request_models import LeadAnalysisRequest, BulkAnalysisRequest, AnalysisRequest, BulkAnalysisRequestSimple
from .response_models import (
    LeadAnalysisResult,
    BulkAnalysisResult,
    HealthCheckResponse,
    ErrorResponse,
    WebsiteAnalysis,
    BusinessOpportunity,
)

__all__ = [
    "LeadAnalysisRequest",
    "BulkAnalysisRequest",
    "AnalysisRequest",
    "BulkAnalysisRequestSimple",
    "LeadAnalysisResult",
    "BulkAnalysisResult",
    "HealthCheckResponse",
    "ErrorResponse",
    "WebsiteAnalysis",
    "BusinessOpportunity",
]
