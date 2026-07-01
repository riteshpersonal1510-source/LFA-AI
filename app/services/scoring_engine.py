"""Scoring engine for the AI Analysis Service."""

from typing import Optional

from ..utils.constants import (
    REVIEW_COUNT_LOW,
    SCORE_LOW_REVIEWS,
    SCORE_MISSING_META_DESCRIPTION,
    SCORE_MISSING_META_TITLE,
    SCORE_NO_CONTACT_PAGE,
    SCORE_NO_SSL,
    SCORE_NO_SOCIAL_LINKS,
    SCORE_NO_WEBSITE,
    SCORE_OUTDATED_WEBSITE,
    SCORE_SLOW_WEBSITE,

    WEBSITE_STATUS_AVERAGE,
    WEBSITE_STATUS_BROKEN,
    WEBSITE_STATUS_MODERN,
    WEBSITE_STATUS_NO_WEBSITE,
    WEBSITE_STATUS_OUTDATED,
)
from ..utils.scoring_helpers import (
    calculate_base_score,
    get_qualification_level,
)


class ScoringEngine:
    """Engine for calculating lead scores and qualifications."""
    
    @staticmethod
    def calculate_score(
        website_status: Optional[str] = None,
        ssl_enabled: Optional[bool] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        has_contact_page: Optional[bool] = None,
        has_social_links: Optional[bool] = None,
        response_time: Optional[int] = None,
        reviews_count: Optional[int] = None,
    ) -> int:
        """
        Calculate lead score based on website analysis factors.
        
        Args:
            website_status: Status of the website (modern, outdated, broken, etc.)
            ssl_enabled: Whether the website has SSL enabled
            meta_title: Website meta title
            meta_description: Website meta description
            has_contact_page: Whether website has a contact page
            has_social_links: Whether website has social media links
            response_time: Website response time in milliseconds
            reviews_count: Number of reviews for the business
            
        Returns:
            Calculated lead score (0-100)
        """
        return calculate_base_score(
            website_status=website_status or WEBSITE_STATUS_AVERAGE,
            ssl_enabled=ssl_enabled if ssl_enabled is not None else True,
            meta_title=meta_title,
            meta_description=meta_description,
            has_contact_page=has_contact_page if has_contact_page is not None else True,
            has_social_links=has_social_links if has_social_links is not None else True,
            response_time=response_time,
            reviews_count=reviews_count,
        )
    
    @staticmethod
    def get_qualification(score: int) -> str:
        """
        Get qualification level based on lead score.
        
        Args:
            score: Lead score (0-100)
            
        Returns:
            Qualification level (high-potential, medium-potential, low-potential)
        """
        return get_qualification_level(score)
    
    @staticmethod
    def normalize_score(score: int) -> int:
        """
        Normalize score to 0-100 range.
        
        Args:
            score: Raw score
            
        Returns:
            Normalized score (0-100)
        """
        return max(0, min(100, score))
    
    @staticmethod
    def get_score_details(score: int) -> dict:
        """
        Get detailed score breakdown.
        
        Args:
            score: Lead score
            
        Returns:
            Score breakdown details
        """
        qualification = get_qualification_level(score)
        
        if score >= 80:
            tier = "excellent"
            comment = "Excellent digital presence"
        elif score >= 60:
            tier = "good"
            comment = "Good potential with some improvements needed"
        elif score >= 40:
            tier = "fair"
            comment = "Fair digital presence with significant improvements needed"
        else:
            tier = "poor"
            comment = "Poor digital presence, immediate action recommended"
        
        return {
            "score": score,
            "qualification": qualification,
            "tier": tier,
            "comment": comment,
        }
