"""WhatsApp Template Service — single source of truth for message templates.

Loads templates from MongoDB `whatsapp_templates` collection, caches them
in memory, and provides placeholder rendering.  This is the ONLY place where
WhatsApp message templates are loaded.  config.py is never used for templates.
"""

import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

DEFAULT_WEBSITE_TEMPLATE = (
    "Hi {{businessName}},\n\n"
    "I came across your website {{website}} and was impressed by your online presence. "
    "I specialize in helping businesses like yours grow with modern web solutions "
    "and digital marketing strategies.\n\n"
    "Would you be open to a quick chat about how we can take your online presence "
    "to the next level?\n\n"
    "Looking forward to hearing from you!\n\n"
    "Best regards,\n"
    "{{senderName}}\n"
    "{{senderPhone}}"
)

DEFAULT_NO_WEBSITE_TEMPLATE = (
    "Hi {{businessName}},\n\n"
    "I noticed your business on {{category}} and wanted to reach out. "
    "I specialize in website development and digital marketing, helping businesses "
    "like yours establish a strong online presence.\n\n"
    "A professional website can help you attract more customers and grow your business. "
    "Would you be interested in discussing how we can create a website for your business?\n\n"
    "Looking forward to hearing from you!\n\n"
    "Best regards,\n"
    "{{senderName}}\n"
    "{{senderPhone}}"
)

COLLECTION_NAME = "whatsapp_templates"


class TemplateService:
    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._cache: dict[str, Optional[str]] = {
            "website": None,
            "no_website": None,
        }
        self._cache_loaded: bool = False

    def set_database(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def _seed_defaults(self) -> None:
        if self._db is None:
            return
        existing_website = await self._db[COLLECTION_NAME].find_one({"type": "website"})
        if existing_website is None:
            logger.info("[TemplateService] Seeding default website template")
            await self._db[COLLECTION_NAME].update_one(
                {"type": "website"},
                {"$set": {"message": DEFAULT_WEBSITE_TEMPLATE, "name": "Website Template"}},
                upsert=True,
            )
        existing_no_website = await self._db[COLLECTION_NAME].find_one({"type": "no_website"})
        if existing_no_website is None:
            logger.info("[TemplateService] Seeding default no-website template")
            await self._db[COLLECTION_NAME].update_one(
                {"type": "no_website"},
                {"$set": {"message": DEFAULT_NO_WEBSITE_TEMPLATE, "name": "No Website Template"}},
                upsert=True,
            )

    async def load_templates(self, force: bool = False) -> dict[str, str]:
        if self._cache_loaded and not force:
            return {
                "website": self._cache["website"] or "",
                "no_website": self._cache["no_website"] or "",
            }

        if self._db is None:
            logger.error("[TemplateService] MongoDB not connected — cannot load templates")
            raise RuntimeError("MongoDB not connected")

        await self._seed_defaults()

        website_doc = await self._db[COLLECTION_NAME].find_one({"type": "website"})
        no_website_doc = await self._db[COLLECTION_NAME].find_one({"type": "no_website"})

        website_msg = ""
        no_website_msg = ""

        if website_doc and website_doc.get("message"):
            website_msg = website_doc["message"]
            logger.info("[TemplateService] Loaded Website Template from MongoDB (id=%s)", website_doc.get("_id"))
        else:
            logger.error("[TemplateService] Website template not found in MongoDB")
            raise ValueError("Website template not found in MongoDB — please save a template from the UI")

        if no_website_doc and no_website_doc.get("message"):
            no_website_msg = no_website_doc["message"]
            logger.info("[TemplateService] Loaded No-Website Template from MongoDB (id=%s)", no_website_doc.get("_id"))
        else:
            logger.error("[TemplateService] No-Website template not found in MongoDB")
            raise ValueError("No-Website template not found in MongoDB — please save a template from the UI")

        self._cache["website"] = website_msg
        self._cache["no_website"] = no_website_msg
        self._cache_loaded = True

        return {
            "website": website_msg,
            "no_website": no_website_msg,
        }

    def refresh_cache(self) -> None:
        self._cache_loaded = False
        self._cache = {"website": None, "no_website": None}
        logger.info("[TemplateService] Cache invalidated — templates will be reloaded from MongoDB on next request")

    async def get_website_template(self) -> str:
        templates = await self.load_templates()
        return templates["website"]

    async def get_no_website_template(self) -> str:
        templates = await self.load_templates()
        return templates["no_website"]

    def get_sender_info(self) -> dict[str, str]:
        import os
        return {
            "name": os.environ.get("SENDER_NAME", ""),
            "phone": os.environ.get("SENDER_PHONE", ""),
            "email": os.environ.get("SENDER_EMAIL", ""),
            "website": os.environ.get("SENDER_WEBSITE", ""),
        }

    def replace_placeholders(self, message: str, lead: dict) -> str:
        now = datetime.now()
        date_str = now.strftime("%d-%b-%Y")
        time_str = now.strftime("%I:%M %p")

        sender = self.get_sender_info()

        owner_name = ""
        raw_owner = lead.get("ownerNames")
        if isinstance(raw_owner, list) and len(raw_owner) > 0:
            owner_name = str(raw_owner[0])
        elif raw_owner:
            owner_name = str(raw_owner)

        business_name = lead.get("companyName") or lead.get("businessName") or ""
        company_name = lead.get("companyName") or lead.get("businessName") or ""

        replacements = {
            "{{businessName}}": business_name,
            "{{ownerName}}": owner_name,
            "{{city}}": lead.get("city") or lead.get("searchedCity") or "",
            "{{area}}": lead.get("area") or lead.get("searchedArea") or "",
            "{{state}}": lead.get("state") or lead.get("searchedState") or "",
            "{{website}}": lead.get("website") or "",
            "{{phone}}": lead.get("phone") or "",
            "{{category}}": lead.get("category") or "",
            "{{rating}}": str(lead.get("rating") or ""),
            "{{leadScore}}": str(lead.get("leadScore") or ""),
            "{{companyName}}": company_name,
            "{{senderName}}": sender["name"],
            "{{senderPhone}}": sender["phone"],
            "{{senderEmail}}": sender["email"],
            "{{senderWebsite}}": sender["website"],
            "{{currentDate}}": date_str,
            "{{currentTime}}": time_str,
        }

        result = message
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)

        return result

    async def render_message(self, lead: dict) -> str:
        has_website = bool(lead.get("hasWebsite") or lead.get("hasRealWebsite"))

        logger.info("[TemplateService] Template Source = MongoDB")

        if has_website:
            template = await self.get_website_template()
            logger.info("[TemplateService] Using Website Template for %s", lead.get("companyName", "unknown"))
        else:
            template = await self.get_no_website_template()
            logger.info("[TemplateService] Using No-Website Template for %s", lead.get("companyName", "unknown"))

        message = self.replace_placeholders(template, lead)
        logger.info("[TemplateService] Final Message Generated for %s", lead.get("companyName", "unknown"))

        return message

    async def render_preview(self, template_type: str, template_text: str, sample_lead: Optional[dict] = None) -> str:
        if sample_lead is None:
            sample_lead = {
                "companyName": "ABC Gym",
                "businessName": "ABC Gym",
                "ownerNames": ["Rahul Sharma"],
                "city": "Ahmedabad",
                "searchedCity": "Ahmedabad",
                "searchedArea": "SG Highway",
                "searchedState": "Gujarat",
                "website": "https://abcgym.com",
                "phone": "+91 98765 43210",
                "category": "Fitness Center",
                "rating": 4.5,
                "leadScore": 92,
            }
        return self.replace_placeholders(template_text, sample_lead)


template_service = TemplateService()
