"""Phone number normalization and validation for WhatsApp automation."""
import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_COUNTRY_CODE = "91"


def normalize_phone(phone: str) -> str:
    """Normalize phone number to standard format."""
    if not phone:
        return ""

    original = phone.strip()

    original = original.replace(' ', '')
    original = original.replace('(', '').replace(')', '')
    original = original.replace('-', '')
    original = original.replace('.', '')

    original = original.replace('+', '')

    cleaned = re.sub(r'\D', '', original)

    if not cleaned:
        return ""

    if cleaned.startswith('00'):
        cleaned = cleaned[2:]

    if cleaned.startswith('0'):
        cleaned = cleaned[1:]

    if cleaned.startswith('91'):
        cleaned = cleaned[2:]

    if len(cleaned) == 10:
        cleaned = DEFAULT_COUNTRY_CODE + cleaned

    if len(cleaned) < 10:
        return ""

    if len(cleaned) > 15:
        return ""

    if not cleaned.startswith('91'):
        cleaned = DEFAULT_COUNTRY_CODE + cleaned

    return cleaned


def validate_phone(phone: str) -> tuple[bool, str]:
    """Validate and normalize phone number."""
    normalized = normalize_phone(phone) if phone else ""
    if not normalized:
        return False, "Empty phone number"
    if len(normalized) < 10:
        return False, f"Too short ({len(normalized)} digits)"
    if len(normalized) > 15:
        return False, f"Too long ({len(normalized)} digits)"

    digits = normalized[2:]

    if len(digits) != 10:
        return False, f"Mobile number must be 10 digits, got {len(digits)}"

    prefix = digits[0]
    if prefix not in ['6', '7', '8', '9']:
        return False, f"Invalid mobile prefix: {prefix}"

    return True, normalized


def is_valid_indian_mobile(phone: str) -> bool:
    """Quick validation for Indian mobile numbers."""
    normalized = normalize_phone(phone) if phone else ""
    if not normalized:
        return False

    digits = normalized[2:]
    if len(digits) != 10:
        return False

    prefix = digits[0]
    return prefix in ['6', '7', '8', '9']
