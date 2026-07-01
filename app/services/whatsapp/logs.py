"""MongoDB logging for WhatsApp automation events."""

import time
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

COLLECTION_NAME = "whatsapp_logs"


class WhatsAppLogger:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self._db = db

    def set_database(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db

    async def log_event(
        self,
        session_id: str,
        lead_id: str,
        company_name: str,
        phone: Optional[str],
        status: str,
        message: Optional[str] = None,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        attempt: int = 0,
        browser_state: str = "",
    ) -> str:
        if self._db is None:
            logger.warning("MongoDB not connected; log entry not stored")
            return "no-db"

        entry = {
            "sessionId": session_id,
            "leadId": lead_id,
            "companyName": company_name,
            "phone": phone or "",
            "status": status,
            "message": message or "",
            "error": error or "",
            "durationMs": duration_ms,
            "attempt": attempt,
            "browserState": browser_state,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "createdAt": time.time(),
        }

        try:
            result = await self._db[COLLECTION_NAME].insert_one(entry)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Failed to store log entry: {e}")
            return "store-failed"

    async def get_session_logs(
        self,
        session_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        if self._db is None:
            return []

        try:
            cursor = (
                self._db[COLLECTION_NAME]
                .find({"sessionId": session_id})
                .sort("createdAt", 1)
                .skip(offset)
                .limit(limit)
            )
            logs = await cursor.to_list(length=limit)
            for log in logs:
                log["_id"] = str(log["_id"])
            return logs
        except Exception as e:
            logger.error(f"Failed to retrieve logs: {e}")
            return []

    async def get_recent_logs(
        self, limit: int = 50, session_id: Optional[str] = None
    ) -> list[dict]:
        if self._db is None:
            return []

        try:
            query = {}
            if session_id:
                query["sessionId"] = session_id
            cursor = (
                self._db[COLLECTION_NAME]
                .find(query)
                .sort("createdAt", -1)
                .limit(limit)
            )
            logs = await cursor.to_list(length=limit)
            for log in logs:
                log["_id"] = str(log["_id"])
            return logs
        except Exception as e:
            logger.error(f"Failed to retrieve recent logs: {e}")
            return []


whatsapp_logger = WhatsAppLogger()
