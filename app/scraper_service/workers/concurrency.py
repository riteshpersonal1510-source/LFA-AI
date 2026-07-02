from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional

from scraper_service.utils.logger import logger


class AsyncWorkerPool:
    def __init__(self, max_concurrency: int = 3) -> None:
        self.max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, items: List[Any], worker: Callable[[Any], Any]) -> List[Any]:
        async def run_one(item: Any) -> Any:
            async with self._semaphore:
                return await worker(item)

        return await asyncio.gather(*[run_one(item) for item in items])


class WorkerManager:
    def __init__(self, max_concurrency: int = 3) -> None:
        self.max_concurrency = max_concurrency
        self.pool = AsyncWorkerPool(max_concurrency=max_concurrency)

    async def run_many(self, items: List[Any], worker: Callable[[Any], Any]) -> List[Any]:
        return await self.pool.run(items, worker)
