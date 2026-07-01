"""In-memory async queue for WhatsApp automation jobs."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SendStatus(str, Enum):
    PREPARED = "prepared"
    OPENING = "opening"
    WAITING = "waiting"
    SENDING = "sending"
    SENT = "sent"
    RETRYING = "retrying"
    FAILED = "failed"


@dataclass
class WhatsAppJob:
    lead_id: str
    company_name: str
    phone: Optional[str]
    message: str
    status: JobStatus = JobStatus.PENDING
    send_status: SendStatus = SendStatus.PREPARED
    error: Optional[str] = None
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class WhatsAppQueue:
    def __init__(self):
        self._jobs: list[WhatsAppJob] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()

    @property
    def total(self) -> int:
        return len(self._jobs)

    @property
    def completed_count(self) -> int:
        return sum(1 for j in self._jobs if j.status == JobStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        return sum(1 for j in self._jobs if j.status == JobStatus.FAILED)

    @property
    def pending_count(self) -> int:
        return sum(1 for j in self._jobs if j.status == JobStatus.PENDING)

    async def enqueue(self, job: WhatsAppJob) -> None:
        async with self._lock:
            self._jobs.append(job)

    async def enqueue_batch(self, jobs: list[WhatsAppJob]) -> None:
        async with self._lock:
            self._jobs.extend(jobs)

    async def dequeue(self) -> Optional[WhatsAppJob]:
        async with self._lock:
            for i in range(self._current_index, len(self._jobs)):
                job = self._jobs[i]
                if job.status == JobStatus.PENDING:
                    job.status = JobStatus.PROCESSING
                    self._current_index = i + 1
                    return job
            return None

    async def mark_completed(self, job: WhatsAppJob) -> None:
        async with self._lock:
            job.status = JobStatus.COMPLETED
            job.completed_at = time.time()

    async def mark_failed(self, job: WhatsAppJob, error: str) -> None:
        async with self._lock:
            job.status = JobStatus.FAILED
            job.error = error
            job.completed_at = time.time()

    async def update_send_status(self, job: WhatsAppJob, send_status: SendStatus) -> None:
        async with self._lock:
            job.send_status = send_status

    async def get_progress(self) -> dict:
        async with self._lock:
            return {
                "total": self.total,
                "completed": self.completed_count,
                "failed": self.failed_count,
                "pending": self.pending_count,
            }

    async def get_jobs(self) -> list[dict]:
        async with self._lock:
            return [
                {
                    "leadId": j.lead_id,
                    "companyName": j.company_name,
                    "phone": j.phone,
                    "status": j.send_status.value,
                    "attempts": j.attempts,
                    "error": j.error,
                }
                for j in self._jobs
            ]

    async def reset(self) -> None:
        async with self._lock:
            self._jobs.clear()
            self._current_index = 0

    async def peek(self) -> list[WhatsAppJob]:
        async with self._lock:
            return list(self._jobs)


whatsapp_queue = WhatsAppQueue()


class CampaignStatus(str, Enum):
    PREPARING = "PREPARING"
    PREPARED = "PREPARED"
    FAILED = "FAILED"


class CampaignQueue:
    def __init__(self):
        self._statuses = {}

    def get_status(self, campaign_id: str) -> dict:
        return self._statuses.get(campaign_id, {"status": "UNKNOWN", "prepared": 0, "failed": 0})

    def update_status(self, campaign_id: str, status: CampaignStatus, prepared: int = 0, failed: int = 0) -> None:
        self._statuses[campaign_id] = {
            "status": status.value,
            "prepared": prepared,
            "failed": failed,
        }


campaign_queue = CampaignQueue()
