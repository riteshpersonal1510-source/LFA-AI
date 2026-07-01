"""MongoDB lead loader for WhatsApp automation."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION_NAME = "leads"

REQUIRED_FIELDS = {
    "companyName": 1,
    "phone": 1,
    "website": 1,
    "searchedCity": 1,
    "searchedArea": 1,
    "searchedState": 1,
    "category": 1,
    "hasWebsite": 1,
    "hasRealWebsite": 1,
    "websiteStatus": 1,
    "email": 1,
    "source": 1,
    "ownerNames": 1,
    "rating": 1,
    "leadScore": 1,
    "_id": 1,
}


class LeadLoader:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    def set_database(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def load_by_ids(self, lead_ids: list[str]) -> list[dict]:
        if self._db is None:
            raise RuntimeError("MongoDB not connected")

        logger.info(f"[DEBUG] Database: {self._db.name}")
        logger.info(f"[DEBUG] Collection: {COLLECTION_NAME}")
        logger.info(f"[DEBUG] Incoming lead IDs: {lead_ids}")

        from bson.objectid import ObjectId

        object_ids = []
        invalid_ids = []
        for lid in lead_ids:
            try:
                object_ids.append(ObjectId(lid))
            except Exception:
                invalid_ids.append(lid)

        if invalid_ids:
            logger.warning(f"Invalid lead IDs: {invalid_ids}")

        if not object_ids:
            return []

        try:
            cursor = self._db[COLLECTION_NAME].find(
                {"_id": {"$in": object_ids}},
                REQUIRED_FIELDS,
            )
            leads = await cursor.to_list(length=len(object_ids))
            return leads
        except Exception as e:
            logger.error(f"Failed to load leads: {e}")
            raise

    async def load_by_ids_batched(
        self, lead_ids: list[str], batch_size: int = 50
    ) -> list[dict]:
        all_leads = []
        for i in range(0, len(lead_ids), batch_size):
            batch = lead_ids[i : i + batch_size]
            leads = await self.load_by_ids(batch)
            all_leads.extend(leads)
        return all_leads

    def normalize_lead(self, lead: dict) -> dict:
        raw = lead.get("_id", {})
        if isinstance(raw, dict):
            oid = str(raw.get("$oid", ""))
        else:
            oid = str(raw)

        return {
            "id": oid,
            "companyName": lead.get("companyName", ""),
            "phone": lead.get("phone", ""),
            "website": lead.get("website", ""),
            "city": lead.get("searchedCity", ""),
            "area": lead.get("searchedArea", ""),
            "state": lead.get("searchedState", ""),
            "category": lead.get("category", ""),
            "hasWebsite": bool(lead.get("hasWebsite", False) or lead.get("hasRealWebsite", False)),
            "websiteStatus": lead.get("websiteStatus", ""),
            "email": lead.get("email", ""),
            "source": lead.get("source", ""),
            "ownerNames": lead.get("ownerNames", []),
            "rating": lead.get("rating"),
            "leadScore": lead.get("leadScore"),
        }


lead_loader = LeadLoader()
