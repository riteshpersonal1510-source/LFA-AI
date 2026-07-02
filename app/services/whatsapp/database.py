"""Persistent MongoDB connection for the WhatsApp automation engine.

The background ``_run_campaign`` task needs a stable connection that
survives beyond the HTTP request/response cycle.  This module provides
a singleton async client that is opened on first use and must be closed
explicitly during app shutdown.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect(mongodb_uri: str, database_name: str) -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is not None:
        logger.debug("[DB] Reusing existing MongoDB connection")
        return _db

    logger.info("[DB] Connecting to MongoDB at %s...", mongodb_uri[:30])
    _client = AsyncIOMotorClient(
        mongodb_uri,
        maxPoolSize=10,
        serverSelectionTimeoutMS=5000,
    )
    _db = _client[database_name]

    # Verify connection
    try:
        await _client.admin.command("ping")
        logger.info("[DB] MongoDB connection established — database: %s", database_name)
    except Exception as e:
        logger.error("[DB] MongoDB ping failed: %s", e)
        _client.close()
        _client = None
        _db = None
        raise RuntimeError(f"MongoDB ping failed: {e}") from e

    return _db


async def disconnect() -> None:
    global _client, _db
    if _client:
        logger.info("[DB] Closing MongoDB connection...")
        _client.close()
        _client = None
        _db = None
        logger.info("[DB] MongoDB connection closed")


def get_db() -> Optional[AsyncIOMotorDatabase]:
    return _db
