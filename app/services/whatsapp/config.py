"""WhatsApp messaging configuration — operational settings only.

IMPORTANT: Message templates are NOT stored here.  They are loaded from
MongoDB (`whatsapp_templates` collection) by TemplateService.
See template_service.py for template loading and rendering.
"""

from dataclasses import dataclass


@dataclass
class WhatsAppConfig:
    sender_name: str = "Lead Finder Agent"
    max_retries: int = 3
    retry_delay_seconds: int = 5
    batch_size: int = 50


config = WhatsAppConfig()
