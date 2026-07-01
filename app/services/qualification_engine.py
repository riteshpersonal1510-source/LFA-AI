"""Qualification engine for the AI Analysis Service."""

from typing import List, Optional

from ..utils.scoring_helpers import (
    get_business_opportunities,
    get_qualification_level,
    get_website_weaknesses,
)


class QualificationEngine:
    """Engine for qualifying leads and generating opportunity suggestions."""
    
    @staticmethod
    def qualify_lead(
        score: int,
        weaknesses: List[str],
        opportunities: List[str],
    ) -> dict:
        """
        Qualify a lead based on score and analysis.
        
        Args:
            score: Lead score (0-100)
            weaknesses: List of website weaknesses
            opportunities: List of business opportunities
            
        Returns:
            Qualification result with summary
        """
        qualification = get_qualification_level(score)
        
        # Generate summary based on qualification
        summary = QualificationEngine._generate_summary(
            qualification=qualification,
            weaknesses=weaknesses,
            opportunities=opportunities,
        )
        
        return {
            "score": score,
            "qualification": qualification,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "summary": summary,
        }
    
    @staticmethod
    def _generate_summary(
        qualification: str,
        weaknesses: List[str],
        opportunities: List[str],
    ) -> str:
        """
        Generate professional summary based on qualification.
        
        Args:
            qualification: Qualification level
            weaknesses: List of weaknesses
            opportunities: List of opportunities
            
        Returns:
            Professional summary string
        """
        if qualification == "high-potential":
            return "Business has strong digital presence and is well-positioned for growth. Recommended for immediate follow-up."
        elif qualification == "medium-potential":
            return "Business has room for improvement in digital presence. Recommended for nurturing and targeted outreach."
        else:
            return "Business has outdated website infrastructure and weak digital presence. Strong potential for redesign and SEO improvement services."
    
    @staticmethod
    def analyze_business(
        website_status: Optional[str] = None,
        ssl_enabled: Optional[bool] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
        has_contact_page: Optional[bool] = None,
        has_social_links: Optional[bool] = None,
        response_time: Optional[int] = None,
        reviews_count: Optional[int] = None,
    ) -> dict:
        """
        Perform comprehensive business analysis.
        
        Args:
            website_status: Website status
            ssl_enabled: SSL enabled flag
            meta_title: Meta title
            meta_description: Meta description
            has_contact_page: Has contact page flag
            has_social_links: Has social links flag
            response_time: Response time in ms
            reviews_count: Number of reviews
            
        Returns:
            Complete business analysis result
        """
        # Calculate weaknesses
        weaknesses = get_website_weaknesses(
            ssl_enabled=ssl_enabled if ssl_enabled is not None else True,
            meta_title=meta_title,
            meta_description=meta_description,
            has_contact_page=has_contact_page if has_contact_page is not None else True,
            has_social_links=has_social_links if has_social_links is not None else True,
            response_time=response_time,
            reviews_count=reviews_count,
            website_status=website_status or "average-website",
        )
        
        # Calculate opportunities
        opportunities = get_business_opportunities(
            weaknesses=weaknesses,
            website_status=website_status or "average-website",
            has_contact_page=has_contact_page if has_contact_page is not None else True,
            has_social_links=has_social_links if has_social_links is not None else True,
        )
        
        # Get score (will be calculated by scoring engine)
        from .scoring_engine import ScoringEngine
        
        score = ScoringEngine.calculate_score(
            website_status=website_status,
            ssl_enabled=ssl_enabled,
            meta_title=meta_title,
            meta_description=meta_description,
            has_contact_page=has_contact_page,
            has_social_links=has_social_links,
            response_time=response_time,
            reviews_count=reviews_count,
        )
        
        # Qualify the lead
        qualification_result = QualificationEngine.qualify_lead(
            score=score,
            weaknesses=weaknesses,
            opportunities=opportunities,
        )
        
        return qualification_result
