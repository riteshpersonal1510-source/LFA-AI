"""Website analysis engine for the AI Analysis Service."""

from typing import Optional

from ..utils.constants import (
    RESPONSE_TIME_FAST,
    RESPONSE_TIME_MODERATE,
    RESPONSE_TIME_SLOW,
    WEBSITE_STATUS_AVERAGE,
    WEBSITE_STATUS_BROKEN,
    WEBSITE_STATUS_MODERN,
    WEBSITE_STATUS_NO_WEBSITE,
    WEBSITE_STATUS_OUTDATED,
)


class WebsiteAnalysisEngine:
    """Engine for analyzing website quality and status."""
    
    @staticmethod
    def analyze_website_status(
        website_status: Optional[str] = None,
        ssl_enabled: Optional[bool] = None,
        has_contact_page: Optional[bool] = None,
        has_social_links: Optional[bool] = None,
        response_time: Optional[int] = None,
    ) -> str:
        """
        Analyze and determine website status.
        
        Args:
            website_status: Provided website status
            ssl_enabled: Whether SSL is enabled
            has_contact_page: Whether contact page exists
            has_social_links: Whether social links exist
            response_time: Website response time
            
        Returns:
            Determined website status
        """
        # If status is provided, validate and return
        if website_status:
            return website_status
        
        # Default status
        default_status = WEBSITE_STATUS_AVERAGE
        
        # Check for issues that downgrade status
        if ssl_enabled is False:
            default_status = WEBSITE_STATUS_OUTDATED
        
        if has_contact_page is False:
            default_status = WEBSITE_STATUS_OUTDATED
        
        if has_social_links is False:
            default_status = WEBSITE_STATUS_OUTDATED
        
        if response_time and response_time > RESPONSE_TIME_SLOW:
            default_status = WEBSITE_STATUS_OUTDATED
        
        return default_status
    
    @staticmethod
    def get_ssl_status(ssl_enabled: Optional[bool]) -> str:
        """
        Get SSL status string.
        
        Args:
            ssl_enabled: Whether SSL is enabled
            
        Returns:
            SSL status string
        """
        if ssl_enabled is None:
            return "unknown"
        return "enabled" if ssl_enabled else "disabled"
    
    @staticmethod
    def get_performance_rating(response_time: Optional[int]) -> str:
        """
        Get performance rating based on response time.
        
        Args:
            response_time: Response time in milliseconds
            
        Returns:
            Performance rating
        """
        if response_time is None:
            return "unknown"
        
        if response_time <= RESPONSE_TIME_FAST:
            return "excellent"
        elif response_time <= RESPONSE_TIME_MODERATE:
            return "good"
        elif response_time <= RESPONSE_TIME_SLOW:
            return "fair"
        return "poor"
    
    @staticmethod
    def check_seo_metadata(
        meta_title: Optional[str],
        meta_description: Optional[str],
    ) -> dict:
        """
        Check SEO metadata quality.
        
        Args:
            meta_title: Website meta title
            meta_description: Website meta description
            
        Returns:
            SEO metadata status
        """
        result = {
            "hasMetaTitle": False,
            "hasMetaDescription": False,
            "titleLength": 0,
            "descriptionLength": 0,
            "seoScore": 0,
        }
        
        if meta_title:
            result["hasMetaTitle"] = True
            result["titleLength"] = len(meta_title)
            if 30 <= len(meta_title) <= 60:
                result["seoScore"] += 10
        
        if meta_description:
            result["hasMetaDescription"] = True
            result["descriptionLength"] = len(meta_description)
            if 120 <= len(meta_description) <= 160:
                result["seoScore"] += 10
        
        return result
