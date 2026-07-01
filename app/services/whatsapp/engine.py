"""WhatsApp automation engine — orchestrates lead loading, message building, sending.

Phase 4 — sequential tab lifecycle:
  - Strict one-tab enforcement with pre-open and post-close verification
  - Granular status flow: queued → opening_whatsapp → opening_chat → typing
                              → sending → sent → verified → completed
  - Never stops the queue on individual failures
"""

import asyncio
import gc
import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from .config import config
from .lead_loader import lead_loader
from .logs import whatsapp_logger
from .message_builder import message_builder
from .template_service import template_service
from .phone_utils import validate_phone
from .sender import SendState, whatsapp_sender
from .session import (
    LeadEntry,
    LeadStatus,
    SessionState,
    session_manager,
)

logger = logging.getLogger(__name__)

_running_campaigns: dict[str, asyncio.Task] = {}

_SEQUENTIAL_STEPS = [
    "queued",
    "opening_whatsapp",
    "opening_chat",
    "typing",
    "sending",
    "sent",
    "verified",
    "completed",
]


class WhatsAppEngine:
    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._sender = whatsapp_sender

    def set_database(self, db: AsyncIOMotorDatabase) -> None:
        self._db = db
        lead_loader.set_database(db)
        whatsapp_logger.set_database(db)

    # ── Phase 1: prepare ──────────────────────────────────────────────

    async def prepare_automation(self, lead_ids: list[str]) -> dict:
        session = session_manager.create(lead_ids)
        session_manager.update_state(session.id, SessionState.LOADING)

        logger.info("[PREPARE] Session %s: loading %d leads", session.id, len(lead_ids))

        if not lead_ids:
            error_msg = "No lead IDs provided"
            logger.error("[PREPARE] %s", error_msg)
            session_manager.mark_failed(session.id, error_msg)
            return session_manager.get_progress(session.id)

        try:
            await template_service.load_templates()
            logger.info("[PREPARE] Loaded templates from MongoDB")
        except Exception as e:
            error_msg = f"Failed to load templates: {str(e)}"
            logger.error("[PREPARE] %s", error_msg)
            session_manager.mark_failed(session.id, error_msg)
            return session_manager.get_progress(session.id)

        try:
            leads = await lead_loader.load_by_ids_batched(
                lead_ids, batch_size=config.batch_size
            )
            logger.info("[PREPARE] Loaded %d leads from %d IDs", len(leads), len(lead_ids))
        except Exception as e:
            error_msg = f"Failed to load leads from database: {str(e)}"
            logger.error("[PREPARE] %s", error_msg, exc_info=True)
            session_manager.mark_failed(session.id, error_msg)
            return session_manager.get_progress(session.id)

        if not leads:
            error_msg = f"No leads found for {len(lead_ids)} IDs (check if IDs are valid MongoDB ObjectIds)"
            logger.error("[PREPARE] %s", error_msg)
            session_manager.mark_failed(session.id, error_msg)
            return session_manager.get_progress(session.id)

        session_manager.update_state(session.id, SessionState.BUILDING)
        logger.info("[PREPARE] Building messages for %d leads", len(leads))

        logs = []
        prepared_count = 0
        failed_count = 0

        for idx, lead in enumerate(leads):
            lead_id = lead.get("id") or str(lead.get("_id", ""))
            company_name = lead.get("companyName", "Unknown")
            phone = lead.get("phone")
            website = lead.get("website", "")
            city = lead.get("city", "")
            has_website = lead.get("hasWebsite", False)
            message_type = "Website" if has_website else "No Website"

            log_entry = {
                "leadId": lead_id,
                "companyName": company_name,
                "phone": phone,
            }

            try:
                message = await message_builder.build(lead)
                log_entry["message"] = message
                log_entry["status"] = "template_generated"
            except Exception as e:
                error_reason = f"Template generation failed: {str(e)}"
                log_entry["status"] = "failed"
                log_entry["error"] = error_reason
                logs.append(log_entry)
                session_manager.increment_failed(session.id)
                await whatsapp_logger.log_event(
                    session_id=session.id,
                    lead_id=lead_id,
                    company_name=company_name,
                    phone=phone,
                    status="failed",
                    error=error_reason,
                )
                failed_count += 1
                logger.warn("[PREPARE] Lead %s template generation failed: %s", lead_id, error_reason)
                continue

            entry = LeadEntry(
                lead_id=lead_id,
                company_name=company_name,
                phone=phone,
                message=message,
                message_type=message_type,
                website=website,
                city=city,
                queue_position=idx + 1,
            )
            entry.status = LeadStatus.QUEUED
            session_manager.add_lead(session.id, entry)

            log_entry["status"] = "queued"
            logs.append(log_entry)
            prepared_count += 1

            await whatsapp_logger.log_event(
                session_id=session.id,
                lead_id=lead_id,
                company_name=company_name,
                phone=phone,
                status="queued",
                message=message,
            )

        if prepared_count == 0:
            error_msg = f"No valid leads prepared (loaded {len(leads)}, all failed template generation)"
            logger.error("[PREPARE] %s", error_msg)
            session_manager.mark_failed(session.id, error_msg)
            progress = session_manager.get_progress(session.id)
            progress["logs"] = logs
            return progress

        session_manager.update_state(session.id, SessionState.READY)
        logger.info("[PREPARE] Campaign ready: %d prepared, %d failed", prepared_count, failed_count)
        progress = session_manager.get_progress(session.id)
        progress["logs"] = logs
        return progress

    # ── Campaign background loop (strict sequential) ──────────────────

    async def _run_campaign(self, session_id: str) -> None:
        session = session_manager.get(session_id)
        if not session:
            logger.error("[CAMPAIGN] Session %s not found for campaign — aborting", session_id)
            return

        total = session.total_leads
        logger.info("[CAMPAIGN] ====== CAMPAIGN STARTED ======")
        logger.info("[CAMPAIGN] Session ID: %s", session_id)
        logger.info("[CAMPAIGN] Total leads: %d", total)
        logger.info("[CAMPAIGN] Queue size: %d", len(session.leads))
        logger.info("[CAMPAIGN] Template Source = MongoDB")
        session_manager.mark_campaign_started(session_id)
        session_manager.set_current_step(session_id, "queued")
        logger.info("[CAMPAIGN] Queue created with %d leads", total)

        for idx, entry in enumerate(list(session.leads.values()), start=1):
            session = session_manager.get(session_id)
            if not session:
                logger.warn("[CAMPAIGN] Session disappeared — stopping")
                break

            logger.info("[CAMPAIGN] --- Lead %d/%d ---", idx, total)
            logger.info("[CAMPAIGN] Queue position: %d", entry.queue_position)
            logger.info("[CAMPAIGN] Lead ID: %s", entry.lead_id)
            logger.info("[CAMPAIGN] Company: %s", entry.company_name)
            logger.info("[CAMPAIGN] Phone: %s", entry.phone)
            logger.info("[CAMPAIGN] Message type: %s", entry.message_type)
            logger.info("[CAMPAIGN] Current step: %s", entry.status)

            # ── Stop / logout check ──────────────────────────────────
            if session.state in (SessionState.STOPPED, SessionState.LOGGED_OUT):
                logger.info("[CAMPAIGN] Session state=%s — stopping loop", session.state)
                break

            # ── Skip already-sent leads ──────────────────────────────
            if entry.status in (LeadStatus.SENT, LeadStatus.VERIFIED, LeadStatus.COMPLETED):
                logger.info("[CAMPAIGN] Lead %s already sent — skipping", entry.lead_id)
                continue

            # ── No phone → fast-fail ─────────────────────────────────
            if not entry.phone:
                logger.warn("[CAMPAIGN] Lead %s has no phone — marking failed", entry.lead_id)
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.FAILED,
                    error="No phone number",
                )
                session_manager.increment_failed(session_id)
                await self._log_send(session_id, entry, "failed", error="No phone number")
                continue

            # ── Phone validation ─────────────────────────────────────
            valid, result = validate_phone(entry.phone)
            if not valid:
                logger.warn("[CAMPAIGN] Lead %s invalid phone '%s': %s",
                            entry.lead_id, entry.phone, result)
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.INVALID_NUMBER,
                    error=result,
                )
                session_manager.increment_failed(session_id)
                await self._log_send(session_id, entry, "invalid_number", error=result)
                continue
            normalized_phone = result
            logger.info("[CAMPAIGN] Phone validated: %s → %s", entry.phone, normalized_phone)

            # ── Set current lead ─────────────────────────────────────
            logger.info("[CAMPAIGN] Processing lead %d/%d: %s", idx, total, entry.company_name)
            session_manager.set_current_lead(session_id, entry.lead_id)
            session_manager.set_current_step(session_id, "opening_whatsapp")
            session_manager.set_lead_status(session_id, entry.lead_id, LeadStatus.OPENING_WHATSAPP)

            # ── Status callback for sender granular updates ──────────
            def cb(status: str):
                session_manager.set_lead_status(session_id, entry.lead_id, status)
                session_manager.set_current_step(session_id, status)

            # ── Send ─────────────────────────────────────────────────
            logger.info("[CAMPAIGN] Invoking sender for %s...", entry.company_name)
            try:
                result = await self._sender.send(
                    phone=normalized_phone,
                    message=entry.message,
                    status_callback=cb,
                )
                logger.info("[CAMPAIGN] Sender returned: success=%s state=%s duration=%.0fms",
                            result.success, result.state, result.duration_ms)
            except Exception as exc:
                logger.exception("[CAMPAIGN] SENDER CRASH for %s", entry.lead_id)
                logger.error("[CAMPAIGN] Exception: %s", exc, exc_info=True)
                result = type("R", (), {
                    "success": False, "state": SendState.FAILED,
                    "error": str(exc), "attempts": 0, "duration_ms": 0,
                    "browser_state": "exception",
                })()

            # ── Terminal: logged out ─────────────────────────────────
            if result.state == SendState.LOGGED_OUT:
                logger.error("[CAMPAIGN] FATAL: WhatsApp logged out — stopping campaign")
                session_manager.mark_logged_out(session_id)
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.FAILED,
                    error=result.error, browser_state=result.browser_state,
                )
                session_manager.increment_failed(session_id)
                await self._log_send(
                    session_id, entry, "logged_out",
                    error=result.error,
                    duration_ms=result.duration_ms,
                    attempt=result.attempts,
                    browser_state=result.browser_state,
                )
                break

            # ── Normal: completed / failed ───────────────────────────
            if result.success:
                logger.info("[CAMPAIGN] ✓ Lead %s COMPLETED (%.0fms)",
                            entry.company_name, result.duration_ms)
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.VERIFIED,
                    duration_ms=result.duration_ms,
                    browser_state=result.browser_state,
                )
                session_manager.set_current_step(session_id, "completed")
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.COMPLETED,
                )
                session_manager.increment_completed(session_id)
                await self._log_send(
                    session_id, entry, "completed",
                    duration_ms=result.duration_ms,
                    attempt=result.attempts,
                    browser_state=result.browser_state,
                )
            else:
                logger.warn("[CAMPAIGN] ✗ Lead %s FAILED: %s",
                            entry.company_name, result.error)
                session_manager.set_lead_status(
                    session_id, entry.lead_id, LeadStatus.FAILED,
                    error=result.error,
                    duration_ms=result.duration_ms,
                    browser_state=result.browser_state,
                )
                session_manager.increment_failed(session_id)
                await self._log_send(
                    session_id, entry, "failed",
                    error=result.error,
                    duration_ms=result.duration_ms,
                    attempt=result.attempts,
                    browser_state=result.browser_state,
                )

            # ── Log queue state ──────────────────────────────────────
            remaining = total - idx
            completed = session.completed_leads
            failed = session.failed_leads
            logger.info("[CAMPAIGN] Queue: %d remaining | %d completed | %d failed | %d total",
                        remaining, completed, failed, total)

            # ── Per-lead memory cleanup ──────────────────────────────
            gc.collect()
            logger.debug("[CAMPAIGN] GC collected")

        # ── Finalise ──────────────────────────────────────────────────
        session = session_manager.get(session_id)
        if session and session.state not in (SessionState.STOPPED, SessionState.LOGGED_OUT):
            session_manager.mark_completed(session_id)
            session_manager.set_current_step(session_id, "completed")
            logger.info("[CAMPAIGN] ====== CAMPAIGN COMPLETED ======")
            logger.info("[CAMPAIGN] Final: %d completed, %d failed out of %d",
                        session.completed_leads, session.failed_leads, session.total_leads)
        elif session:
            logger.info("[CAMPAIGN] ====== CAMPAIGN ENDED (state=%s) ======", session.state)

        _running_campaigns.pop(session_id, None)

    async def _log_send(
        self,
        session_id: str,
        entry: LeadEntry,
        status: str,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        attempt: int = 0,
        browser_state: str = "",
    ) -> None:
        try:
            await whatsapp_logger.log_event(
                session_id=session_id,
                lead_id=entry.lead_id,
                company_name=entry.company_name,
                phone=entry.phone,
                status=status,
                message=entry.message,
                error=error,
                duration_ms=duration_ms,
                attempt=attempt,
                browser_state=browser_state,
            )
        except Exception as e:
            logger.warning("Failed to persist log: %s", e)

    # ── Public API ────────────────────────────────────────────────────

    async def start_campaign(self, lead_ids: list[str]) -> dict:
        logger.info("[ENGINE] ====== START CAMPAIGN REQUESTED =====")
        logger.info("[ENGINE] Lead IDs count: %d", len(lead_ids))
        for lid in lead_ids:
            logger.debug("[ENGINE]   Lead ID: %s", lid)

        if not lead_ids or len(lead_ids) == 0:
            logger.error("[ENGINE] No lead IDs provided")
            from ...core.exception_handlers import ValidationException
            raise ValidationException("No leads selected for campaign")

        display_available = self._sender._check_display_available()
        if not display_available:
            logger.warn("[ENGINE] Display not available - campaign may not send actual messages. Display warning to user.")

        result = await self.prepare_automation(lead_ids)
        session_id = result.get("sessionId", "")
        status = result.get("status", "")
        
        logger.info("[ENGINE] prepare_automation result: status=%s sessionId=%s totalLeads=%d",
                    status, session_id, result.get("totalLeads", 0))

        if status == SessionState.FAILED:
            error_msg = result.get("error", "Failed to prepare automation")
            logger.error("[ENGINE] prepare_automation failed: %s — aborting campaign", error_msg)
            return result

        if not session_id:
            logger.error("[ENGINE] No session ID returned from prepare_automation")
            from ...core.exception_handlers import WhatsAppException
            raise WhatsAppException("Failed to create campaign session", "SESSION_CREATION_FAILED", 500)

        if result.get("totalLeads", 0) == 0:
            logger.error("[ENGINE] No leads to process after preparation")
            result["error"] = "No valid leads found to process"
            result["status"] = SessionState.FAILED
            return result

        logger.info("[ENGINE] Creating background task for campaign %s with %d leads...", 
                    session_id, result.get("totalLeads", 0))
        task = asyncio.create_task(self._run_campaign(session_id))
        _running_campaigns[session_id] = task
        logger.info("[ENGINE] Background task created and queued for %s", session_id)

        progress = session_manager.get_progress(session_id)
        logger.info("[ENGINE] Campaign started: session=%s status=%s totalLeads=%d",
                    session_id, progress.get("status"), progress.get("totalLeads"))
        logger.info("[ENGINE] ====== START CAMPAIGN RETURNING =====")
        return progress

    async def stop_campaign(self, session_id: str) -> bool:
        session = session_manager.get(session_id)
        if not session:
            return False
        if session.state != SessionState.RUNNING:
            return False

        session_manager.mark_stopped(session_id)

        task = _running_campaigns.pop(session_id, None)
        if task and not task.done():
            task.cancel()

        return True


whatsapp_engine = WhatsAppEngine()
