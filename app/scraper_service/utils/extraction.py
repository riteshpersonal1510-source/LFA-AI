"""
Shared extraction helpers — email, phone, social links.
Mirrors the logic from Node.js:
  - backend/src/utils/email-extract.ts
  - backend/src/services/phone-extraction.service.ts
  - backend/src/services/social-extractor.service.ts
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.ASCII
)

_SOCIAL_EMAIL_DOMAINS: Set[str] = {
    "gmail.com", "yahoo.com", "yahoo.co.in", "outlook.com", "hotmail.com",
    "rediffmail.com", "rediff.com", "live.com", "ymail.com", "inbox.com",
    "protonmail.com", "proton.me", "zoho.com", "fastmail.com",
    "aol.com", "mail.com", "icloud.com",
}

_JUNK_LOCAL_PARTS: Set[str] = {
    "abuse", "noreply", "no-reply", "donotreply", "do-not-reply",
    "spam", "postmaster", "hostmaster", "webmaster",
}

_BUSINESS_PREFIXES: Set[str] = {
    "info", "contact", "support", "sales", "hello", "care", "enquiry",
    "inquiry", "help", "admin", "office", "business", "connect",
    "reach", "team", "mail", "feedback", "service", "career",
    "hr", "jobs", "partner", "marketing",
}


def extract_emails(text: str) -> List[str]:
    """Return unique, deduplicated business emails from arbitrary text."""
    seen: Set[str] = set()
    results: List[str] = []
    for match in _EMAIL_RE.finditer(text):
        email = match.group(0)
        lower = email.lower()
        if lower in seen:
            continue
        seen.add(lower)
        local, _, domain = lower.partition("@")
        if local in _JUNK_LOCAL_PARTS:
            continue
        results.append(email)
    return results


def is_business_email(email: str) -> bool:
    domain = email.lower().split("@")[-1] if "@" in email else ""
    return domain not in _SOCIAL_EMAIL_DOMAINS and bool(domain)


# ---------------------------------------------------------------------------
# Phone
# ---------------------------------------------------------------------------

_PHONE_PATTERNS = [
    re.compile(r"(?:\+?91[\s.\-]?)?[6-9]\d{9}"),          # India
    re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"),  # US/CA
    re.compile(r"(?:\+?44[\s.\-]?)?\d{4}[\s.\-]?\d{3}[\s.\-]?\d{4}"),  # UK
    re.compile(r"(?:\+?61[\s.\-]?)?\d{4}[\s.\-]?\d{3}[\s.\-]?\d{3}"),  # AU
    re.compile(r"(?:\+?971[\s.\-]?)?\d{1,3}[\s.\-]?\d{3,4}[\s.\-]?\d{4}"),  # UAE
    re.compile(r"(?:\+?65[\s.\-]?)?\d{4}[\s.\-]?\d{4}"),  # SG
]

_WA_PATTERNS = [
    re.compile(r"wa\.me/(\d+)"),
    re.compile(r"api\.whatsapp\.com/send\?phone=(\d+)"),
    re.compile(r"whatsapp\.com/send\?phone=(\d+)"),
]


def normalize_phone(raw: str) -> str:
    """Normalise a raw phone string to E.164-ish format."""
    cleaned = re.sub(r"[\s\-\(\)\.]", "", raw)
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if 10 <= len(digits) <= 15:
        return f"+{digits}"
    return raw.strip()


def is_valid_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return 10 <= len(digits) <= 15


def extract_phones(text: str) -> List[str]:
    found: Set[str] = set()
    for pattern in _PHONE_PATTERNS:
        for match in pattern.finditer(text):
            normalized = normalize_phone(match.group(0))
            if is_valid_phone(normalized):
                found.add(normalized)
    return list(found)


def extract_whatsapp_number(html: str) -> Optional[str]:
    for pat in _WA_PATTERNS:
        m = pat.search(html)
        if m:
            number = re.sub(r"\D", "", m.group(1))
            if len(number) >= 10:
                return f"+{number}"
    return None


def select_primary_phone(phones: List[str]) -> str:
    if not phones:
        return ""
    indian = [p for p in phones if p.startswith("+91")]
    return (indian or phones)[0]


# ---------------------------------------------------------------------------
# Social Links
# ---------------------------------------------------------------------------

_SOCIAL_DOMAINS: Dict[str, str] = {
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
    "wa.me": "whatsapp",
    "whatsapp.com": "whatsapp",
    "telegram.me": "telegram",
    "t.me": "telegram",
}


def extract_social_links(links: List[str]) -> Dict[str, str]:
    """Return a {platform: url} dict from a list of href values."""
    result: Dict[str, str] = {}
    for href in links:
        lower = href.lower()
        for domain, platform in _SOCIAL_DOMAINS.items():
            if domain in lower and platform not in result:
                result[platform] = href
    return result


# ---------------------------------------------------------------------------
# Lead score (mirrors backend/src/core/scraper-engine/lead-storage.ts)
# ---------------------------------------------------------------------------

def calculate_lead_score(lead: dict) -> int:
    score = 0
    if lead.get("website"):
        score += 20
    if lead.get("phone"):
        score += 15
    if lead.get("email"):
        score += 15
    if lead.get("address"):
        score += 10
    if lead.get("streetAddress"):
        score += 3
    if lead.get("postalCode"):
        score += 2
    if lead.get("category"):
        score += 5
    if lead.get("secondaryCategories"):
        score += 3
    rating = lead.get("rating") or 0
    if rating > 0:
        score += 5
    reviews = lead.get("reviewsCount") or 0
    if reviews > 0:
        score += 5
    if reviews > 50:
        score += 3
    if lead.get("workingHours"):
        score += 5
    if lead.get("businessStatus"):
        score += 3
    if lead.get("plusCode"):
        score += 2
    if lead.get("latitude") is not None and lead.get("longitude") is not None:
        score += 3
    if lead.get("serviceOptions"):
        score += 2
    if lead.get("ownerClaimed"):
        score += 2
    return min(score, 100)
