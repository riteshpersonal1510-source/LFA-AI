"""Async scrape job manager for the AI service scraper router."""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from scraper_service.models.scrape_models import ScrapeResponse
from scraper_service.utils.logger import logger


@dataclass
class ScrapeJob:
    job_id: str
    session_id: str
    status: str = "queued"
    message: str = "Job queued"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    task: Optional[asyncio.Task] = None
    new_leads: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobId": self.job_id,
            "sessionId": self.session_id,
            "status": self.status,
            "message": self.message,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.created_at)),
            "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.updated_at)),
            "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.started_at)) if self.started_at else None,
            "completedAt": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.completed_at)) if self.completed_at else None,
            "result": self.result,
            "error": self.error,
        }


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs: Dict[str, ScrapeJob] = {}

    def create_job(self, job_id: str, session_id: str, message: str = "Job queued") -> ScrapeJob:
        job = ScrapeJob(job_id=job_id, session_id=session_id, message=message)
        with self._lock:
            self._jobs[job_id] = job
        logger.info(
            "[JOB] Created job %s for session %s at %s",
            job_id,
            session_id,
            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(job.created_at)),
        )
        return job

    def get_job(self, job_id: str) -> Optional[ScrapeJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def mark_running(self, job_id: str, message: str = "Job running") -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.message = message
            job.started_at = time.time()
            job.updated_at = job.started_at
        logger.info(
            "[JOB] Job %s transitioned queued->running at %s",
            job_id,
            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(job.started_at)),
        )

    def add_lead(self, job_id: str, lead: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.new_leads.append(lead)

    def heartbeat(self, job_id: str, stage: Optional[str] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.updated_at = time.time()
            if stage:
                job.message = stage

    def consume_leads(self, job_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return []
            leads = job.new_leads
            job.new_leads = []
            return leads

    def complete(self, job_id: str, result: ScrapeResponse) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "completed"
            job.message = result.message or "Job completed"
            job.result = result.dict()
            job.completed_at = time.time()
            job.updated_at = job.completed_at
        logger.info(
            "[JOB] Job %s transitioned running->completed at %s",
            job_id,
            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(job.completed_at)),
        )

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "failed"
            job.message = error
            job.error = error
            job.completed_at = time.time()
            job.updated_at = job.completed_at
        logger.error(
            "[JOB] Job %s transitioned running->failed at %s: %s",
            job_id,
            time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(job.completed_at)),
            error,
        )

    def set_message(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.message = message
            job.updated_at = time.time()

    def start_background_task(self, job_id: str, coro: Any) -> None:
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        async def _run():
            self.mark_running(job_id)
            try:
                result = await coro
                self.complete(job_id, result)
            except Exception as exc:
                self.fail(job_id, str(exc))
                logger.exception("[JOB] Background task for job %s failed", job_id)

        task = asyncio.create_task(_run())
        with self._lock:
            job.task = task


job_manager = JobManager()
