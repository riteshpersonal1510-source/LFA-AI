"""In-memory session state management for WhatsApp automation."""

import time
from typing import Dict, List, Optional
from uuid import uuid4


class SessionState:
    CREATED = "created"
    LOADING = "loading"
    BUILDING = "building"
    QUEUING = "queuing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    LOGGED_OUT = "logged_out"


class LeadStatus:
    """Granular statuses for the Phase-4 sequential tab lifecycle."""

    QUEUED = "queued"
    OPENING_WHATSAPP = "opening_whatsapp"
    OPENING_CHAT = "opening_chat"
    TYPING = "typing"
    SENDING = "sending"
    SENT = "sent"
    VERIFIED = "verified"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    INVALID_NUMBER = "invalid_number"
    RATE_LIMITED = "rate_limited"


class LeadEntry:
    def __init__(
        self,
        lead_id: str,
        company_name: str,
        phone: Optional[str],
        message: str,
        message_type: str = "Website",
        website: str = "",
        city: str = "",
        queue_position: int = 0,
    ):
        self.lead_id: str = lead_id
        self.company_name: str = company_name
        self.phone: Optional[str] = phone
        self.message: str = message
        self.message_type: str = message_type
        self.website: str = website
        self.city: str = city
        self.queue_position: int = queue_position
        self.status: str = LeadStatus.QUEUED
        self.error: Optional[str] = None
        self.attempts: int = 0
        self.duration_ms: float = 0.0
        self.browser_state: str = ""
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.completed_at: Optional[float] = None


class Session:
    def __init__(self, lead_ids: list[str]):
        self.id: str = uuid4().hex[:12]
        self.lead_ids: list[str] = lead_ids
        self.state: str = SessionState.CREATED
        self.total_leads: int = len(lead_ids)
        self.completed_leads: int = 0
        self.failed_leads: int = 0
        self.current_lead_index: int = 0
        self.current_lead_id: Optional[str] = None
        self.current_step: str = ""
        self.leads: Dict[str, LeadEntry] = {}
        self.logs: list[dict] = []
        self.error: Optional[str] = None
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None
        self.campaign_started_at: Optional[float] = None
        self.total_duration_ms: float = 0.0


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self, lead_ids: list[str]) -> Session:
        session = Session(lead_ids)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def update_state(self, session_id: str, state: str) -> None:
        session = self.get(session_id)
        if session:
            session.state = state

    def mark_campaign_started(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.campaign_started_at = time.time()
            session.state = SessionState.RUNNING

    def increment_completed(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.completed_leads += 1
            session.current_lead_index = session.completed_leads + session.failed_leads

    def increment_failed(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.failed_leads += 1
            session.current_lead_index = session.completed_leads + session.failed_leads

    def set_current_lead(self, session_id: str, lead_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.current_lead_id = lead_id

    def set_current_step(self, session_id: str, step: str) -> None:
        session = self.get(session_id)
        if session:
            session.current_step = step

    def add_log(self, session_id: str, log_entry: dict) -> None:
        session = self.get(session_id)
        if session:
            session.logs.append(log_entry)

    def mark_completed(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.state = SessionState.COMPLETED
            session.completed_at = time.time()

    def mark_failed(self, session_id: str, error: str) -> None:
        session = self.get(session_id)
        if session:
            session.state = SessionState.FAILED
            session.error = error
            session.completed_at = time.time()

    def mark_stopped(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.state = SessionState.STOPPED
            session.completed_at = time.time()

    def mark_logged_out(self, session_id: str) -> None:
        session = self.get(session_id)
        if session:
            session.state = SessionState.LOGGED_OUT
            session.completed_at = time.time()

    def add_lead(self, session_id: str, entry: LeadEntry) -> None:
        session = self.get(session_id)
        if session:
            session.leads[entry.lead_id] = entry

    def set_lead_status(
        self,
        session_id: str,
        lead_id: str,
        status: str,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
        browser_state: str = "",
    ) -> None:
        session = self.get(session_id)
        if session and lead_id in session.leads:
            entry = session.leads[lead_id]
            entry.status = status
            entry.updated_at = time.time()
            if error:
                entry.error = error
            if duration_ms:
                entry.duration_ms = duration_ms
            if browser_state:
                entry.browser_state = browser_state
            if status in (
                LeadStatus.SENT,
                LeadStatus.VERIFIED,
                LeadStatus.COMPLETED,
                LeadStatus.FAILED,
                LeadStatus.INVALID_NUMBER,
            ):
                entry.attempts += 1
                if status in (LeadStatus.COMPLETED, LeadStatus.FAILED):
                    entry.completed_at = time.time()

    def _compute_eta(self, session) -> Optional[float]:
        processed = session.completed_leads + session.failed_leads
        if processed == 0 or not session.campaign_started_at:
            return None
        elapsed = time.time() - session.campaign_started_at
        avg_per_lead = elapsed / processed
        remaining = session.total_leads - processed
        return avg_per_lead * remaining

    def get_progress(self, session_id: str) -> Optional[dict]:
        session = self.get(session_id)
        if not session:
            return None

        eta = self._compute_eta(session)

        return {
            "sessionId": session.id,
            "status": session.state,
            "totalLeads": session.total_leads,
            "completed": session.completed_leads,
            "failed": session.failed_leads,
            "currentLead": session.current_lead_id,
            "currentLeadIndex": session.current_lead_index,
            "currentStep": session.current_step,
            "error": session.error,
            "eta": eta,
            "createdAt": session.created_at,
            "completedAt": session.completed_at,
        }

    def get_detailed_progress(self, session_id: str) -> Optional[dict]:
        session = self.get(session_id)
        if not session:
            return None

        eta = self._compute_eta(session)
        processed = session.completed_leads + session.failed_leads
        elapsed = 0.0
        if session.campaign_started_at:
            elapsed = time.time() - session.campaign_started_at

        leads_list = []
        for entry in session.leads.values():
            leads_list.append({
                "leadId": entry.lead_id,
                "companyName": entry.company_name,
                "phone": entry.phone,
                "website": entry.website,
                "city": entry.city,
                "messageType": entry.message_type,
                "queuePosition": entry.queue_position,
                "status": entry.status,
                "error": entry.error,
                "attempts": entry.attempts,
                "durationMs": entry.duration_ms,
                "browserState": entry.browser_state,
                "updatedAt": entry.updated_at,
                "completedAt": entry.completed_at,
            })

        return {
            "sessionId": session.id,
            "status": session.state,
            "totalLeads": session.total_leads,
            "completed": session.completed_leads,
            "failed": session.failed_leads,
            "currentLead": session.current_lead_id,
            "currentLeadIndex": session.current_lead_index,
            "currentStep": session.current_step,
            "error": session.error,
            "eta": eta,
            "elapsedSeconds": elapsed,
            "processed": processed,
            "remaining": session.total_leads - processed,
            "leads": leads_list,
            "createdAt": session.created_at,
            "completedAt": session.completed_at,
        }


session_manager = SessionManager()
