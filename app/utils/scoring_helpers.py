"""Scoring helper functions for the AI Analysis Service."""

from typing import Optional

from ..utils.constants import (
    RESPONSE_TIME_FAST,
    RESPONSE_TIME_MODERATE,
    RESPONSE_TIME_SLOW,
    REVIEW_COUNT_LOW,
    SCORE_BROKEN_WEBSITE,
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


def get_website_status_score(website_status: str) -> int:
    """Get score adjustment based on website status."""
    status_scores = {
        WEBSITE_STATUS_NO_WEBSITE: SCORE_NO_WEBSITE,
        WEBSITE_STATUS_BROKEN: SCORE_BROKEN_WEBSITE,
        WEBSITE_STATUS_OUTDATED: SCORE_OUTDATED_WEBSITE,
        WEBSITE_STATUS_AVERAGE: 15,
        WEBSITE_STATUS_MODERN: -10,
    }
    return status_scores.get(website_status, 0)


def get_ssl_score(ssl_enabled: bool) -> int:
    """Get score adjustment based on SSL status."""
    return 0 if ssl_enabled else SCORE_NO_SSL


def get_meta_score(meta_title: Optional[str], meta_description: Optional[str]) -> int:
    """Get score adjustment based on meta tags."""
    score = 0
    if not meta_title or len(meta_title) < 10:
        score += SCORE_MISSING_META_TITLE
    if not meta_description or len(meta_description) < 50:
        score += SCORE_MISSING_META_DESCRIPTION
    return score


def get_contact_score(has_contact_page: bool) -> int:
    """Get score adjustment based on contact page."""
    return 0 if has_contact_page else SCORE_NO_CONTACT_PAGE


def get_social_score(has_social_links: bool) -> int:
    """Get score adjustment based on social links."""
    return 0 if has_social_links else SCORE_NO_SOCIAL_LINKS


def get_response_time_score(response_time: Optional[int]) -> int:
    """Get score adjustment based on response time."""
    if response_time is None:
        return 0
    
    if response_time > RESPONSE_TIME_SLOW:
        return SCORE_SLOW_WEBSITE
    elif response_time > RESPONSE_TIME_MODERATE:
        return SCORE_SLOW_WEBSITE // 2
    return 0


def get_review_score(reviews_count: Optional[int]) -> int:
    """Get score adjustment based on review count."""
    if reviews_count is None or reviews_count < REVIEW_COUNT_LOW:
        return SCORE_LOW_REVIEWS
    return 0


def calculate_base_score(
    website_status: str,
    ssl_enabled: bool,
    meta_title: Optional[str],
    meta_description: Optional[str],
    has_contact_page: bool,
    has_social_links: bool,
    response_time: Optional[int],
    reviews_count: Optional[int],
) -> int:
    """Calculate base score from all factors."""
    score = 50  # Base score
    
    # Add adjustments
    score += get_website_status_score(website_status)
    score += get_ssl_score(ssl_enabled)
    score += get_meta_score(meta_title, meta_description)
    score += get_contact_score(has_contact_page)
    score += get_social_score(has_social_links)
    score += get_response_time_score(response_time)
    score += get_review_score(reviews_count)
    
    # Normalize to 0-100
    return max(0, min(100, score))


def get_qualification_level(score: int) -> str:
    """Get qualification level based on score."""
    if score >= SCORE_HIGH_THRESHOLD:
        return "high-potential"
    elif score >= SCORE_MEDIUM_THRESHOLD:
        return "medium-potential"
    return "low-potential"


def get_website_weaknesses(
    ssl_enabled: bool,
    meta_title: Optional[str],
    meta_description: Optional[str],
    has_contact_page: bool,
    has_social_links: bool,
    response_time: Optional[int],
    reviews_count: Optional[int],
    website_status: str,
) -> list:
    """Generate list of website weaknesses."""
    weaknesses = []
    
    if not ssl_enabled:
        weaknesses.append("Missing SSL certificate")
    
    if not meta_title or len(meta_title) < 10:
        weaknesses.append("Weak or missing meta title")
    
    if not meta_description or len(meta_description) < 50:
        weaknesses.append("Weak or missing meta description")
    
    if not has_contact_page:
        weaknesses.append("No contact page detected")
    
    if not has_social_links:
        weaknesses.append("No social media presence detected")
    
    if response_time and response_time > RESPONSE_TIME_SLOW:
        weaknesses.append("Slow website response time")
    elif response_time and response_time > RESPONSE_TIME_MODERATE:
        weaknesses.append("Moderate website response time")
    
    if reviews_count is not None and reviews_count < REVIEW_COUNT_LOW:
        weaknesses.append("Low review count")
    
    if website_status == WEBSITE_STATUS_OUTDATED:
        weaknesses.append("Outdated website infrastructure")
    elif website_status == WEBSITE_STATUS_BROKEN:
        weaknesses.append("Website has technical issues")
    
    return weaknesses


def get_business_opportunities(
    weaknesses: list,
    website_status: str,
    has_contact_page: bool,
    has_social_links: bool,
) -> list:
    """Generate business opportunity suggestions based on weaknesses."""
    opportunities = []
    
    opportunity_mapping = {
        "Missing SSL certificate": "Digital presence improvement",
        "Weak or missing meta title": "SEO optimization opportunity",
        "Weak or missing meta description": "SEO optimization opportunity",
        "No contact page detected": "Website redesign opportunity",
        "No social media presence detected": "Social media presence opportunity",
        "Slow website response time": "Mobile optimization opportunity",
        "Moderate website response time": "Mobile optimization opportunity",
        "Low review count": "Content update opportunity",
        "Outdated website infrastructure": "Website redesign opportunity",
        "Website has technical issues": "Website redesign opportunity",
    }
    
    for weakness in weaknesses:
        if weakness in opportunity_mapping:
            opportunity = opportunity_mapping[weakness]
            if opportunity not in opportunities:
                opportunities.append(opportunity)
    
    # Additional opportunities based on status
    if website_status == WEBSITE_STATUS_NO_WEBSITE:
        opportunities.append("Website creation opportunity")
    
    if not has_contact_page and "Website redesign opportunity" not in opportunities:
        opportunities.append("Website redesign opportunity")
    
    if not has_social_links and "Social media presence opportunity" not in opportunities:
        opportunities.append("Social media presence opportunity")
    
    return opportunities
