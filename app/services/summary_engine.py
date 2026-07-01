"""Summary engine for the AI Analysis Service."""

from typing import List, Optional

from ..utils.constants import (
    OPPORTUNITY_TEMPLATES,
)


class SummaryEngine:
    """Engine for generating professional summaries."""
    
    @staticmethod
    def generate_summary(
        qualification_level: str,
        weaknesses: List[str],
        opportunities: List[str],
        website_status: Optional[str] = None,
        score: Optional[int] = None,
    ) -> str:
        """
        Generate professional analysis summary.
        
        Args:
            qualification_level: Lead qualification level
            weaknesses: List of website weaknesses
            opportunities: List of business opportunities
            website_status: Website status
            score: Lead score
            
        Returns:
            Professional summary string
        """
        # Build summary parts
        parts = []
        
        # Opening based on qualification
        if qualification_level == "high-potential":
            parts.append("Business demonstrates strong digital presence and online performance.")
        elif qualification_level == "medium-potential":
            parts.append("Business has solid foundation but shows room for digital optimization.")
        else:
            parts.append("Business has outdated website infrastructure and weak digital presence.")
        
        # Add weakness summary if present
        if weaknesses:
            weakness_summary = SummaryEngine._summarize_weaknesses(weaknesses)
            parts.append(weakness_summary)
        
        # Add opportunity summary
        if opportunities:
            opportunity_summary = SummaryEngine._summarize_opportunities(opportunities)
            parts.append(opportunity_summary)
        
        # Combine into final summary
        summary = " ".join(parts)
        
        # Ensure proper punctuation
        if not summary.endswith("."):
            summary += "."
        
        return summary
    
    @staticmethod
    def _summarize_weaknesses(weaknesses: List[str]) -> str:
        """Create weakness summary sentence."""
        if not weaknesses:
            return ""
        
        if len(weaknesses) <= 2:
            weakness_text = " and ".join(weaknesses)
            return f"Key issues identified: {weakness_text}."
        else:
            return f"Multiple issues detected: {weaknesses[0]}, {weaknesses[1]}, and {len(weaknesses) - 2} others."
    
    @staticmethod
    def _summarize_opportunities(opportunities: List[str]) -> str:
        """Create opportunity summary sentence."""
        if not opportunities:
            return ""
        
        opportunity_count = len(opportunities)
        if opportunity_count == 1:
            return f"Opportunity: {opportunities[0]}."
        elif opportunity_count == 2:
            return f"Opportunities: {opportunities[0]} and {opportunities[1]}."
        else:
            return f"Multiple opportunities identified: {opportunities[0]}, {opportunities[1]}, and {opportunity_count - 2} more."
    
    @staticmethod
    def generate_action_items(
        opportunities: List[str],
    ) -> List[str]:
        """
        Generate specific action items from opportunities.
        
        Args:
            opportunities: List of business opportunities
            
        Returns:
            List of specific action items
        """
        action_items = []
        
        for opportunity in opportunities:
            action_item = SummaryEngine._get_action_item(opportunity)
            if action_item:
                action_items.append(action_item)
        
        return action_items
    
    @staticmethod
    def _get_action_item(opportunity: str) -> Optional[str]:
        """Get specific action item for an opportunity."""
        action_mappings = {
            "Website redesign opportunity": "Redesign website with modern UI/UX and mobile-first approach",
            "SEO optimization opportunity": "Implement on-page SEO improvements and content optimization",
            "Mobile optimization opportunity": "Optimize website for mobile devices and improve loading speed",
            "Branding opportunity": "Develop consistent branding across all digital channels",
            "Digital presence improvement": "Strengthen overall digital presence with consistent information",
            "Content update opportunity": "Update website content to reflect current offerings",
            "Social media presence opportunity": "Establish or improve social media presence on key platforms",
            "Email marketing setup opportunity": "Set up email marketing infrastructure for customer engagement",
            "Website creation opportunity": "Create a professional website with comprehensive business information",
            "Social media presence opportunity": "Create social media profiles and post regularly",
            "Website redesign opportunity": "Undertake website redesign to improve user experience",
        }
        return action_mappings.get(opportunity)
