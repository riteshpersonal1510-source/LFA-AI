"""Business opportunity engine for the AI Analysis Service."""

from typing import List, Optional

from ..utils.constants import (
    OPPORTUNITY_BRANDING,
    OPPORTUNITY_CONTENT_UPDATE,
    OPPORTUNITY_DIGITAL_PRESENCE,
    OPPORTUNITY_EMAIL_MARKETING,
    OPPORTUNITY_MOBILE_OPTIMIZATION,
    OPPORTUNITY_SEO_OPTIMIZATION,
    OPPORTUNITY_SOCIAL_MEDIA,
    OPPORTUNITY_WEBSITE_REDESIGN,
    OPPORTUNITY_TEMPLATES,
)


class BusinessOpportunityEngine:
    """Engine for identifying business opportunities from website analysis."""
    
    @staticmethod
    def analyze_opportunities(
        website_status: Optional[str] = None,
        has_contact_page: Optional[bool] = None,
        has_social_links: Optional[bool] = None,
        ssl_enabled: Optional[bool] = None,
        response_time: Optional[int] = None,
        meta_title: Optional[str] = None,
        meta_description: Optional[str] = None,
    ) -> List[str]:
        """
        Analyze business opportunities from website analysis.
        
        Args:
            website_status: Website status
            has_contact_page: Whether contact page exists
            has_social_links: Whether social links exist
            ssl_enabled: SSL enabled status
            response_time: Response time in ms
            meta_title: Meta title
            meta_description: Meta description
            
        Returns:
            List of identified business opportunities
        """
        opportunities = []
        
        # Check for website creation/redesign opportunities
        if website_status in ["no-website", "broken-website"]:
            opportunities.append(OPPORTUNITY_WEBSITE_REDESIGN)
        elif website_status == "outdated-website":
            opportunities.append(OPPORTUNITY_WEBSITE_REDESIGN)
        
        # Check for SEO opportunities
        if not meta_title or len(meta_title) < 10:
            opportunities.append(OPPORTUNITY_SEO_OPTIMIZATION)
        if not meta_description or len(meta_description) < 50:
            opportunities.append(OPPORTUNITY_SEO_OPTIMIZATION)
        
        # Check for mobile optimization opportunities
        if response_time and response_time > 3000:
            opportunities.append(OPPORTUNITY_MOBILE_OPTIMIZATION)
        
        # Check for social media opportunities
        if has_social_links is False:
            opportunities.append(OPPORTUNITY_SOCIAL_MEDIA)
        
        # Check for branding opportunities
        if website_status in ["outdated-website", "broken-website"]:
            opportunities.append(OPPORTUNITY_BRANDING)
        
        # Check for email marketing opportunities
        if has_contact_page is False:
            opportunities.append(OPPORTUNITY_EMAIL_MARKETING)
        
        # Check for digital presence opportunities
        if ssl_enabled is False:
            opportunities.append(OPPORTUNITY_DIGITAL_PRESENCE)
        
        # Deduplicate while preserving order
        seen = set()
        unique_opportunities = []
        for opp in opportunities:
            if opp not in seen:
                seen.add(opp)
                unique_opportunities.append(opp)
        
        return unique_opportunities
    
    @staticmethod
    def get_opportunity_details(opportunity: str) -> dict:
        """
        Get detailed information about a business opportunity.
        
        Args:
            opportunity: Opportunity type
            
        Returns:
            Opportunity details including description
        """
        description = OPPORTUNITY_TEMPLATES.get(
            opportunity,
            f"Improve business {opportunity.lower()}."
        )
        
        return {
            "type": opportunity,
            "description": description,
        }
    
    @staticmethod
    def prioritize_opportunities(
        opportunities: List[str],
        score: Optional[int] = None,
    ) -> List[dict]:
        """
        Prioritize opportunities based on analysis score.
        
        Args:
            opportunities: List of opportunities
            score: Lead score (optional, for prioritization)
            
        Returns:
            Prioritized opportunities with priority level
        """
        if not opportunities:
            return []
        
        # Default priorities
        priority_mapping = {
            OPPORTUNITY_WEBSITE_REDESIGN: "high",
            OPPORTUNITY_DIGITAL_PRESENCE: "high",
            OPPORTUNITY_SOCIAL_MEDIA: "medium",
            OPPORTUNITY_BRANDING: "medium",
            OPPORTUNITY_SEO_OPTIMIZATION: "medium",
            OPPORTUNITY_MOBILE_OPTIMIZATION: "medium",
            OPPORTUNITY_CONTENT_UPDATE: "low",
            OPPORTUNITY_EMAIL_MARKETING: "medium",
        }
        
        # Adjust priorities based on score
        prioritized = []
        for opp in opportunities:
            priority = priority_mapping.get(opp, "low")
            
            # Boost priority for low-score leads
            if score is not None and score < 40 and priority == "low":
                priority = "medium"
            
            prioritized.append({
                "type": opp,
                "priority": priority,
                "description": OPPORTUNITY_TEMPLATES.get(opp, f"Improve {opp.lower()}."),
            })
        
        return prioritized
