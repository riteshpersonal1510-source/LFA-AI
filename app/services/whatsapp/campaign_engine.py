from datetime import datetime, timezone
import logging
from urllib.parse import quote
from bson.objectid import ObjectId
from app.services.whatsapp.database import get_db
from app.services.whatsapp.lead_loader import lead_loader
from app.services.whatsapp.template_engine import template_engine
from app.services.whatsapp.template_service import template_service
from app.services.whatsapp.phone_utils import validate_phone
from app.services.whatsapp.queue import campaign_queue, CampaignStatus

logger = logging.getLogger(__name__)

class CampaignEngine:
    async def generate_campaign(self, campaign_id: str, lead_ids: list[str]) -> dict:
        logger.info("[CampaignEngine] ====== CAMPAIGN STARTED ======")
        logger.info("[CampaignEngine] Campaign ID: %s", campaign_id)
        logger.info("[CampaignEngine] Lead count: %d", len(lead_ids))
        db = get_db()
        campaign_queue.update_status(campaign_id, CampaignStatus.PREPARING, prepared=0, failed=0)

        try:
            await template_service.load_templates(force=True)
            logger.info("[CampaignEngine] Template Source = MongoDB")
            logger.info("[CampaignEngine] Loaded Website Template")
            logger.info("[CampaignEngine] Loaded No Website Template")

            leads = await lead_loader.load_by_ids_batched(lead_ids)
        except Exception as e:
            logger.exception("Failed to load leads or templates")
            campaign_queue.update_status(campaign_id, CampaignStatus.FAILED, prepared=0, failed=len(lead_ids))
            return {"success": False, "prepared": 0, "failed": len(lead_ids), "campaignId": campaign_id, "data": [], "skipped": [], "total": 0, "skippedCount": 0}

        prepared = []
        skipped = []
        prepared_count = 0
        failed_count = 0

        for lead in leads:
            try:
                normalized_lead = lead_loader.normalize_lead(lead)
                lead_id = normalized_lead["id"]
                company = normalized_lead["companyName"]
                phone = normalized_lead["phone"]
                logger.info("[CampaignEngine] Lead Loaded: %s", company)

                valid, result = validate_phone(phone)
                if not valid:
                    skipped.append({"leadId": lead_id, "companyName": company, "reason": result})
                    failed_count += 1

                    if db is not None:
                        await db["leads"].update_one(
                            {"_id": ObjectId(lead_id)},
                            {"$set": {
                                "campaignStatus": "failed",
                                "validationReason": result,
                                "isWhatsAppValid": False,
                                "whatsappOutreach.status": "skipped",
                                "whatsappOutreach.lastError": f"Invalid phone: {result}",
                                "whatsappOutreach.validationReason": result,
                            }}
                        )
                    logger.info("[CampaignEngine] Lead skipped: %s - %s", lead_id, result)
                    continue

                normalized_phone = result
                message, template_used = await template_engine.generate_message(normalized_lead)
                logger.info("[CampaignEngine] Template Selected: %s", template_used)
                logger.info("[CampaignEngine] Message Generated for %s", company)

                encoded = quote(message)
                whatsapp_url = f"https://web.whatsapp.com/send?phone={normalized_phone}&text={encoded}"

                entry = {
                    "leadId": lead_id,
                    "companyName": company,
                    "phone": phone,
                    "normalizedPhone": f"+{normalized_phone}",
                    "message": message,
                    "templateType": "website" if normalized_lead["hasWebsite"] else "no-website",
                    "hasWebsite": normalized_lead["hasWebsite"],
                    "whatsappUrl": whatsapp_url,
                    "skipReason": None,
                }
                prepared.append(entry)

                if db is not None:
                    await db["leads"].update_one(
                        {"_id": ObjectId(lead_id)},
                        {"$set": {
                            "messageStatus": "prepared",
                            "preparedMessage": message,
                            "campaignId": campaign_id,
                            "preparedAt": datetime.now(timezone.utc).isoformat(),
                            "whatsappOutreach.status": "prepared",
                            "whatsappOutreach.templateType": "website" if normalized_lead["hasWebsite"] else "no-website",
                            "whatsappOutreach.campaignId": campaign_id,
                            "whatsappOutreach.preparedMessage": message,
                            "whatsappOutreach.preparedAt": datetime.now(timezone.utc).isoformat(),
                            "whatsappOutreach.lastError": None,
                            "normalizedPhone": normalized_phone,
                            "isWhatsAppValid": True,
                            "validationReason": None,
                            "campaignStatus": "preparing",
                        }}
                    )
                    logger.info("Mongo Updated")

                prepared_count += 1
                campaign_queue.update_status(campaign_id, CampaignStatus.PREPARING, prepared=prepared_count, failed=failed_count)
            except Exception as e:
                logger.exception("Error processing lead")
                failed_count += 1

                if db is not None:
                    await db["leads"].update_one(
                        {"_id": ObjectId(lead_id)},
                        {"$set": {
                            "campaignStatus": "failed",
                            "validationReason": str(e),
                            "isWhatsAppValid": False,
                            "whatsappOutreach.status": "failed",
                            "whatsappOutreach.lastError": str(e),
                        }}
                    )

                campaign_queue.update_status(campaign_id, CampaignStatus.PREPARING, prepared=prepared_count, failed=failed_count)

        campaign_queue.update_status(campaign_id, CampaignStatus.PREPARED, prepared=prepared_count, failed=failed_count)
        logger.info("Campaign Completed")
        logger.info("[CampaignEngine] Summary: %d prepared, %d failed, %d skipped", prepared_count, failed_count, len(skipped))

        return {
            "success": True,
            "prepared": prepared_count,
            "failed": failed_count,
            "campaignId": campaign_id,
            "data": prepared,
            "skipped": skipped,
            "total": len(prepared),
            "skippedCount": len(skipped),
        }

campaign_engine = CampaignEngine()
