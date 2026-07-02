"""
Async browser pool for Playwright.

Provides managed Chromium/Firefox instances with resource cleanup,
idle-timeout eviction, and per-source routing.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from scraper_service.utils.logger import logger
from scraper_service.config.settings import settings

BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-webgl",
    "--disable-accelerated-2d-canvas",
    "--window-size=1920,1080",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet", "imageset", "svg", "beacon"}

BLOCKED_DOMAINS = [
    "google-analytics.com",
    "googletagmanager.com",
    "facebook.net",
    "doubleclick.net",
    "cdn.cookie-script.com",
    "hotjar.com",
    "clarity.ms",
    "bat.bing.com",
]

IDLE_TIMEOUT_S = 120
PAGE_TIMEOUT_MS = 30_000
MAX_PAGES_PER_BROWSER = 5


@dataclass
class PooledBrowser:
    browser: Browser
    context: BrowserContext
    pages: set = field(default_factory=set)
    last_used: float = field(default_factory=time.time)
    in_use: bool = False
    browser_type: str = "chromium"  # "chromium" | "firefox"


class BrowserPool:
    """Async browser pool that reuses contexts across scraping tasks."""

    def __init__(self, max_size: int = 3) -> None:
        self._max_size = max_size
        self._pool: List[PooledBrowser] = []
        self._lock = asyncio.Lock()
        self._playwright: Optional[Playwright] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._started = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        if self._started:
            return
        self._playwright = await async_playwright().start()
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._started = True
        logger.info("BrowserPool started (max_size={})", self._max_size)

    async def shutdown(self) -> None:
        if self._cleanup_task:
            self._cleanup_task.cancel()
        async with self._lock:
            for pb in self._pool:
                await self._destroy(pb)
            self._pool.clear()
        if self._playwright:
            await self._playwright.stop()
        self._started = False
        logger.info("BrowserPool shut down")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def acquire(
        self, source: str, browser_type: str = "chromium"
    ) -> Tuple[Page, BrowserContext, Browser]:
        """Return a new page inside a pooled browser context."""
        async with self._lock:
            pb = self._find_idle(browser_type)
            if pb is None:
                # This will now raise with the original Playwright exception if launch fails
                pb = await self._launch(browser_type)

        pb.in_use = True
        pb.last_used = time.time()

        page = await pb.context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT_MS)
        page.set_default_navigation_timeout(PAGE_TIMEOUT_MS)
        await self._setup_route_blocking(page)
        pb.pages.add(page)

        logger.debug("BrowserPool: page acquired (source={}, pool_size={})", source, len(self._pool))
        return page, pb.context, pb.browser

    async def release(self, page: Page, source: str) -> None:
        """Release a page back to the pool."""
        async with self._lock:
            pb = next((p for p in self._pool if page in p.pages), None)
            if pb:
                pb.pages.discard(page)
                pb.last_used = time.time()
                pb.in_use = len(pb.pages) > 0
        try:
            if not page.is_closed():
                await page.close()
        except Exception:
            pass
        logger.debug("BrowserPool: page released (source={})", source)

    async def reset(self) -> None:
        """Close all browsers and restart the pool."""
        await self.shutdown()
        await self.start()
        logger.info("BrowserPool reset")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_idle(self, browser_type: str) -> Optional[PooledBrowser]:
        return next(
            (
                pb
                for pb in self._pool
                if not pb.in_use
                and len(pb.pages) < MAX_PAGES_PER_BROWSER
                and pb.browser_type == browser_type
            ),
            None,
        )

    async def _launch(self, browser_type: str = "chromium") -> Optional[PooledBrowser]:
        if len(self._pool) >= self._max_size:
            # Evict oldest idle browser
            idle = sorted(
                (pb for pb in self._pool if not pb.in_use),
                key=lambda x: x.last_used,
            )
            if idle:
                await self._destroy(idle[0])
                self._pool.remove(idle[0])
            else:
                raise RuntimeError("BrowserPool: max pool size reached, no idle browsers")

        if self._playwright is None:
            raise RuntimeError("BrowserPool not started — call await pool.start() first")

        try:
            if browser_type == "firefox":
                browser = await self._playwright.firefox.launch(
                    headless=settings.browser_headless,
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    locale="en-US",
                    ignore_https_errors=True,
                )
            else:
                browser = await self._playwright.chromium.launch(
                    headless=settings.browser_headless,
                    args=BROWSER_ARGS,
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=USER_AGENT,
                    locale="en-US",
                    timezone_id="Asia/Kolkata",
                    geolocation={"latitude": 23.0225, "longitude": 72.5714},
                    permissions=["geolocation"],
                    ignore_https_errors=True,
                )

            pb = PooledBrowser(
                browser=browser,
                context=context,
                browser_type=browser_type,
            )
            self._pool.append(pb)
            logger.info(
                "BrowserPool: launched {} browser (pool_size={})",
                browser_type,
                len(self._pool),
            )
            return pb
        except Exception as exc:
            # Log the original exception with full details
            logger.error("BrowserPool: {} launch failed: {} - {}", browser_type, type(exc).__name__, str(exc))
            # Re-raise with original exception details preserved
            raise RuntimeError(f"BrowserPool: failed to launch {browser_type}: {type(exc).__name__}: {str(exc)}") from exc

    async def _setup_route_blocking(self, page: Page) -> None:
        async def handle_route(route):
            url = route.request.url.lower()
            resource_type = route.request.resource_type
            if resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            if any(domain in url for domain in BLOCKED_DOMAINS):
                await route.abort()
                return
            await route.continue_()

        await page.route("**/*", handle_route)

    async def _destroy(self, pb: PooledBrowser) -> None:
        for page in list(pb.pages):
            try:
                if not page.is_closed():
                    await page.close()
            except Exception:
                pass
        pb.pages.clear()
        try:
            await pb.context.close()
        except Exception:
            pass
        try:
            await pb.browser.close()
        except Exception:
            pass

    async def _cleanup_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(30)
                now = time.time()
                async with self._lock:
                    to_remove = [
                        pb
                        for pb in self._pool
                        if not pb.in_use and (now - pb.last_used) > IDLE_TIMEOUT_S
                    ]
                    for pb in to_remove:
                        await self._destroy(pb)
                        self._pool.remove(pb)
                        logger.info(
                            "BrowserPool: evicted idle browser (idle={:.0f}s, pool_size={})",
                            now - pb.last_used,
                            len(self._pool),
                        )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("BrowserPool cleanup error: {}", exc)

    def get_status(self) -> Dict:
        active = sum(1 for pb in self._pool if pb.in_use)
        idle = len(self._pool) - active
        return {"pool_size": len(self._pool), "active": active, "idle": idle}


# Global pool instance — started by the FastAPI lifespan
browser_pool = BrowserPool(max_size=settings.browser_max_pool_size)
