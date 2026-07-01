"""Constants for the AI Analysis Service."""

from typing import Literal

# Website status constants
WEBSITE_STATUS_NO_WEBSITE = "no-website"
WEBSITE_STATUS_BROKEN = "broken-website"
WEBSITE_STATUS_OUTDATED = "outdated-website"
WEBSITE_STATUS_AVERAGE = "average-website"
WEBSITE_STATUS_MODERN = "modern-website"

WEBSITE_STATUSES = [
    WEBSITE_STATUS_NO_WEBSITE,
    WEBSITE_STATUS_BROKEN,
    WEBSITE_STATUS_OUTDATED,
    WEBSITE_STATUS_AVERAGE,
    WEBSITE_STATUS_MODERN,
]

# Qualification level constants
QUALIFICATION_HIGH = "high-potential"
QUALIFICATION_MEDIUM = "medium-potential"
QUALIFICATION_LOW = "low-potential"

QUALIFICATION_LEVELS = [
    QUALIFICATION_HIGH,
    QUALIFICATION_MEDIUM,
    QUALIFICATION_LOW,
]

# Scoring constants
SCORE_NO_WEBSITE = 95
SCORE_BROKEN_WEBSITE = 90
SCORE_NO_SSL = 20
SCORE_MISSING_META_TITLE = 10
SCORE_MISSING_META_DESCRIPTION = 10
SCORE_NO_CONTACT_PAGE = 10
SCORE_NO_SOCIAL_LINKS = 10
SCORE_SLOW_WEBSITE = 15
SCORE_LOW_REVIEWS = 5
SCORE_OUTDATED_WEBSITE = 20

# Score thresholds
SCORE_HIGH_THRESHOLD = 80
SCORE_MEDIUM_THRESHOLD = 50

# Response time thresholds (in milliseconds)
RESPONSE_TIME_FAST = 1000
RESPONSE_TIME_MODERATE = 2000
RESPONSE_TIME_SLOW = 3000
RESPONSE_TIME_VERY_SLOW = 5000

# Review count thresholds
REVIEW_COUNT_LOW = 10
REVIEW_COUNT_MEDIUM = 50
REVIEW_COUNT_HIGH = 100

# Opportunity types
OPPORTUNITY_WEBSITE_REDESIGN = "Website redesign opportunity"
OPPORTUNITY_SEO_OPTIMIZATION = "SEO optimization opportunity"
OPPORTUNITY_MOBILE_OPTIMIZATION = "Mobile optimization opportunity"
OPPORTUNITY_BRANDING = "Branding opportunity"
OPPORTUNITY_DIGITAL_PRESENCE = "Digital presence improvement"
OPPORTUNITY_CONTENT_UPDATE = "Content update opportunity"
OPPORTUNITY_SOCIAL_MEDIA = "Social media presence opportunity"
OPPORTUNITY_EMAIL_MARKETING = "Email marketing setup opportunity"

# Opportunity descriptions
OPPORTUNITY_TEMPLATES = {
    OPPORTUNITY_WEBSITE_REDESIGN: "Business could benefit from a modern website redesign to improve user experience and conversions.",
    OPPORTUNITY_SEO_OPTIMIZATION: "Website SEO needs improvement to increase organic visibility and search rankings.",
    OPPORTUNITY_MOBILE_OPTIMIZATION: "Mobile user experience should be enhanced for better mobile engagement.",
    OPPORTUNITY_BRANDING: "Brand consistency and positioning could be improved across all digital channels.",
    OPPORTUNITY_DIGITAL_PRESENCE: "Overall digital presence needs strengthening with consistent information across platforms.",
    OPPORTUNITY_CONTENT_UPDATE: "Website content should be updated to reflect current offerings and improve engagement.",
    OPPORTUNITY_SOCIAL_MEDIA: "Social media presence should be established or improved to connect with customers.",
    OPPORTUNITY_EMAIL_MARKETING: "Email marketing infrastructure should be set up for customer engagement.",
}

# Analysis categories
CATEGORY_ANALYSIS = "category"
RESPONSE_TIME_ANALYSIS = "response_time"
SSL_ANALYSIS = "ssl"
META_ANALYSIS = "meta"
CONTACT_ANALYSIS = "contact"
SOCIAL_ANALYSIS = "social"
REVIEW_ANALYSIS = "review"

# Error messages
ERROR_NO_WEBSITE = "Website is not accessible or does not exist"
ERROR_CONNECTION_FAILED = "Failed to connect to website"
ERROR_TIMEOUT = "Request timeout"
ERROR_INVALID_INPUT = "Invalid input data"
