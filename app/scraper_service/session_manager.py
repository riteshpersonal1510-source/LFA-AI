"""In-memory search session tracking for scraper progress endpoints."""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SearchSession:
    session_id: str
    keyword: str = ""
    location: str = ""
    status: str = "started"  # started | running | completed | failed
    current_page: int = 0
    current_business: str = ""
    current_source: str = ""
    processed: int = 0
    total: int = 0
    saved: int = 0
    failed: int = 0
    duplicates: int = 0
    percentage: float = 0.0
    completed: bool = False
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        elapsed = max(time.time() - self.started_at, 0.001)
        return {
            "sessionId": self.session_id,
            "status": self.status,
            "keyword": self.keyword,
            "location": self.location,
            "currentPage": self.current_page,
            "currentBusiness": self.current_business,
            "currentSource": self.current_source,
            "processed": self.processed,
            "total": self.total,
            "saved": self.saved,
            "failed": self.failed,
            "duplicates": self.duplicates,
            "percentage": round(self.percentage, 2),
            "completed": self.completed,
            "error": self.error,
            "startedAt": self.started_at,
            "updatedAt": self.updated_at,
            "elapsedSeconds": round(elapsed, 2),
        }


class SessionManager:
    """Thread-safe store for active and recently completed scrape sessions."""

    def __init__(self, max_completed: int = 200) -> None:
        self._lock = threading.Lock()
        self._active: Dict[str, SearchSession] = {}
        self._completed: Dict[str, SearchSession] = {}
        self._max_completed = max_completed

    def create(
        self,
        keyword: str,
        location: str = "",
        session_id: Optional[str] = None,
    ) -> SearchSession:
        session = SearchSession(
            session_id=session_id or f"py_{uuid.uuid4().hex[:8]}",
            keyword=keyword,
            location=location,
            status="started",
        )
        with self._lock:
            self._active[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SearchSession]:
        with self._lock:
            if session_id in self._active:
                return self._active[session_id]
            return self._completed.get(session_id)

    def update(self, session_id: str, **fields: Any) -> Optional[SearchSession]:
        with self._lock:
            session = self._active.get(session_id)
            if not session:
                return self._completed.get(session_id)
            for key, value in fields.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = time.time()
            if session.total > 0:
                session.percentage = min(100.0, (session.processed / session.total) * 100)
            return session

    def mark_running(self, session_id: str, source: str = "") -> None:
        self.update(session_id, status="running", current_source=source)

    def mark_progress(
        self,
        session_id: str,
        *,
        current_business: str = "",
        current_page: int = 0,
        processed: int = 0,
        total: int = 0,
        saved: int = 0,
        failed: int = 0,
    ) -> None:
        self.update(
            session_id,
            status="running",
            current_business=current_business,
            current_page=current_page,
            processed=processed,
            total=total,
            saved=saved,
            failed=failed,
        )

    def complete(self, session_id: str, *, saved: int = 0, failed: int = 0) -> None:
        with self._lock:
            session = self._active.pop(session_id, None)
            if not session:
                return
            session.status = "completed"
            session.completed = True
            session.saved = saved
            session.failed = failed
            session.percentage = 100.0
            session.updated_at = time.time()
            self._completed[session_id] = session
            if len(self._completed) > self._max_completed:
                oldest = sorted(self._completed.values(), key=lambda s: s.updated_at)
                for old in oldest[: len(self._completed) - self._max_completed]:
                    self._completed.pop(old.session_id, None)

    def fail(self, session_id: str, error: str) -> None:
        with self._lock:
            session = self._active.pop(session_id, None)
            if not session:
                session = self._completed.get(session_id)
                if not session:
                    session = SearchSession(session_id=session_id, keyword="", status="failed")
            session.status = "failed"
            session.completed = True
            session.error = error
            session.updated_at = time.time()
            self._completed[session_id] = session


session_manager = SessionManager()
