"""WhatsApp template engine.

Uses TemplateService (MongoDB-backed) as the single source of truth.
config.py is NEVER used for message templates.
"""

import logging

from .template_service import template_service

logger = logging.getLogger(__name__)


class TemplateEngine:
    async def generate_message(self, lead: dict) -> tuple[str, str]:
        company_name = lead.get("companyName") or "there"
        website_exists = bool(lead.get("hasWebsite") or lead.get("hasRealWebsite"))

        message = await template_service.render_message(lead)
        template_used = "HAS WEBSITE TEMPLATE" if website_exists else "NO WEBSITE TEMPLATE"

        return message, template_used


template_engine = TemplateEngine()
