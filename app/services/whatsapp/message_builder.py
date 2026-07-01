"""WhatsApp message template builder.

Uses TemplateService (MongoDB-backed) as the single source of truth.
config.py is NEVER used for message templates.
"""

import logging

from .template_service import template_service

logger = logging.getLogger(__name__)


class MessageBuilder:
    async def build(self, lead: dict) -> str:
        message = await template_service.render_message(lead)
        return message

    async def build_preview(self, lead: dict) -> dict:
        message = await self.build(lead)
        return {
            "companyName": lead.get("companyName", ""),
            "phone": lead.get("phone", ""),
            "hasWebsite": lead.get("hasWebsite", False),
            "website": lead.get("website", ""),
            "city": lead.get("city", ""),
            "message": message,
            "messageLength": len(message),
        }


message_builder = MessageBuilder()
