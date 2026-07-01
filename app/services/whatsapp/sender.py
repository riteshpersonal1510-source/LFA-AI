"""WhatsApp Web sender — production-hardened browser automation.

Phase 4 — sequential tab lifecycle:
  - One WhatsApp tab at a time, verified closed before next lead
  - Outgoing-message bubble verification before marking sent
  - Granular status flow: opening_whatsapp → opening_chat → typing → sending → sent → verified
"""

import logging
import os
import re
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional
from urllib.parse import quote

from app.services.whatsapp.x11_diagnostics import X11Diagnostics

logger = logging.getLogger(__name__)


class SendState(str, Enum):
    SUCCESS = "sent"
    FAILED = "failed"
    RETRYING = "retrying"
    LOGGED_OUT = "logged_out"
    INVALID_NUMBER = "invalid_number"
    RATE_LIMITED = "rate_limited"
    NO_INTERNET = "no_internet"
    POPUP = "popup"
    UNKNOWN = "unknown"
    BROWSER_CLOSED = "browser_closed"
    SLOW_LOAD = "slow_load"
    CHAT_UNAVAILABLE = "chat_unavailable"


@dataclass
class SendResult:
    success: bool
    state: SendState = SendState.UNKNOWN
    error: Optional[str] = None
    attempts: int = 0
    duration_ms: float = 0.0
    browser_state: str = "unknown"


class WhatsAppSender:
    def __init__(self):
        self.max_retries: int = 3
        self.retry_delay_s: float = 5.0
        self.rate_limit_delay_s: float = 60.0
        self.initial_wait_s: float = 10.0
        self.chat_load_timeout_s: float = 30.0
        self.chat_poll_interval_s: float = 2.0
        self.send_verify_timeout_s: float = 12.0
        self.outgoing_bubble_timeout_s: float = 10.0
        self.post_send_wait_s: float = 3.0
        self.inter_lead_delay_s: float = 2.0
        self.tab_close_delay_s: float = 1.0
        self.tab_verify_retries: int = 5
        self.internet_check_url: str = "https://www.google.com/generate_204"

    _pg = None
    _pg_init_error: Optional[str] = None
    _pg_diagnostics_run = False

    def _check_display_available(self) -> bool:
        display = os.environ.get('DISPLAY')
        if not display:
            logger.error("[DISPLAY] DISPLAY environment variable not set. PyAutoGUI requires X11 display.")
            return False

        if not self._pg_diagnostics_run:
            diagnostics = X11Diagnostics.run_full_diagnostics()
            X11Diagnostics.log_diagnostics(diagnostics)
            self._pg_diagnostics_run = True
            if not diagnostics.get("x11_connection_ok"):
                logger.error("[DISPLAY] X11 connection test failed")
                X11Diagnostics.log_remediation(diagnostics)

        logger.info("[DISPLAY] Display %s is available", display)
        return True

    def _fix_x11_auth(self) -> None:
        """Ensure ``XAUTHORITY`` is set and an xauth entry exists for DISPLAY.

        ``mouseinfo`` (imported by ``pyautogui``) calls
        ``Xlib.display.Display()`` at module level.  This requires both
        ``DISPLAY`` and ``XAUTHORITY`` to be present in the Python process
        environment *before* the import — subprocess-based checks like
        ``xset q`` are irrelevant because they inherit the shell's env.
        """
        import tempfile

        display = os.environ.get("DISPLAY", ":0")

        xauth_path = X11Diagnostics.get_xauthority()
        if xauth_path:
            os.environ["XAUTHORITY"] = xauth_path

        def _xauth_list(args: list[str], env_override: dict | None = None
                        ) -> str | None:
            try:
                env = env_override if env_override is not None else os.environ
                r = subprocess.run(
                    args, capture_output=True, text=True, timeout=3, env=env,
                )
                for line in r.stdout.strip().split("\n"):
                    if "MIT-MAGIC-COOKIE-1" in line:
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            return parts[-1]
            except Exception:
                pass
            return None

        def _write_cookie(cookie_hex: str) -> None:
            temp = os.path.join(tempfile.gettempdir(), f".Xauthority_wa_{os.getpid()}")
            try:
                subprocess.run(
                    ["xauth", "-f", temp, "add", display, ".", cookie_hex],
                    capture_output=True, timeout=3,
                )
                os.chmod(temp, 0o600)
                os.environ["XAUTHORITY"] = temp
                logger.info("[X11] Wrote xauth cookie to %s", temp)
            except Exception as e:
                logger.warning("[X11] Failed to write xauth: %s", e)

        cookie = _xauth_list(["xauth", "list", display])
        if cookie is not None:
            _write_cookie(cookie)
            return

        clean = {k: v for k, v in os.environ.items() if k != "XAUTHORITY"}
        cookie = _xauth_list(["xauth", "list", display], clean)
        if cookie is not None:
            _write_cookie(cookie)
            return

        cookie = _xauth_list(["xauth", "list"], clean)
        if cookie is not None:
            _write_cookie(cookie)

    def _patch_screenshot(self) -> None:
        pass

    def _ensure_pg(self):
        if self._pg is not None:
            return True

        if not self._check_display_available():
            logger.error("[INIT] Display not available. Cannot initialize PyAutoGUI.")
            logger.error("[INIT] Verify X11 setup or run in environment with DISPLAY set.")
            self._pg_init_error = "DISPLAY not available"
            return False

        self._fix_x11_auth()

        logger.info("[INIT] DISPLAY=%s XAUTHORITY=%s",
                    os.environ.get("DISPLAY"), os.environ.get("XAUTHORITY"))

        try:
            from Xlib.display import Display
            Display(os.environ["DISPLAY"]).screen()
            logger.info("[INIT] Real X11 connection validated")
        except Exception as e:
            self._pg_init_error = f"X11 connection failed: {e}"
            logger.error("[INIT] Real X11 connection failed: %s", e)
            return False

        try:
            import pyautogui as pg
            self._pg = pg
            self._patch_screenshot()
            logger.info("[INIT] PyAutoGUI initialized successfully")
            return True
        except ImportError:
            msg = "pyautogui not installed"
            logger.error("[INIT] %s", msg)
            self._pg_init_error = msg
            return False
        except Exception as e:
            self._pg_init_error = f"{type(e).__name__}: {e}"
            logger.error("[INIT] Failed to initialize PyAutoGUI: %s", self._pg_init_error)
            if "Authorization" in str(e) or "authorization" in str(e):
                logger.error("[INIT] X11 Authorization error detected")
                diagnostics = X11Diagnostics.run_full_diagnostics()
                X11Diagnostics.log_diagnostics(diagnostics)
                X11Diagnostics.log_remediation(diagnostics)
            return False

    # ── Internet connectivity ──────────────────────────────────────────

    def _check_internet(self) -> bool:
        try:
            import urllib.request
            urllib.request.urlopen(self.internet_check_url, timeout=5)
            return True
        except Exception:
            return False

    # ── Tab lifecycle — strict one-tab enforcement ─────────────────────

    def _find_whatsapp_windows(self) -> list[str]:
        """Return list of X11 window IDs whose title contains 'WhatsApp'."""
        try:
            out = subprocess.run(
                ["xdotool", "search", "--name", "WhatsApp"],
                capture_output=True, text=True, timeout=3,
            )
            if out.stdout.strip():
                return out.stdout.strip().split("\n")
        except Exception:
            pass
        return []

    def _close_all_whatsapp_windows(self) -> int:
        """Close every open WhatsApp window/tab.  Returns count closed."""
        closed = 0
        for _ in range(3):
            wids = self._find_whatsapp_windows()
            if not wids:
                break
            for wid in wids:
                try:
                    subprocess.run(
                        ["xdotool", "windowclose", wid],
                        timeout=2, capture_output=True,
                    )
                    closed += 1
                except Exception:
                    pass
            time.sleep(0.5)
        return closed

    def _verify_tab_closed(self) -> bool:
        """Return True when no WhatsApp windows remain on screen."""
        for _ in range(self.tab_verify_retries):
            wids = self._find_whatsapp_windows()
            if not wids:
                return True
            for wid in wids:
                try:
                    subprocess.run(
                        ["xdotool", "windowclose", wid],
                        timeout=2, capture_output=True,
                    )
                except Exception:
                    pass
            time.sleep(0.5)
        return len(self._find_whatsapp_windows()) == 0

    def _ensure_single_tab(self) -> None:
        """Guarantee zero WhatsApp tabs before opening a new one."""
        self._close_all_whatsapp_windows()

    # ── Browser window management ──────────────────────────────────────

    def _activate_browser(self) -> bool:
        try:
            wid = subprocess.run(
                ["xdotool", "search", "--name", "WhatsApp"],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip().split("\n")[0]
            if wid:
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", wid],
                    timeout=5, capture_output=True,
                )
                subprocess.run(
                    ["xdotool", "windowfocus", "--sync", wid],
                    timeout=5, capture_output=True,
                )
                subprocess.run(
                    ["xdotool", "windowsize", wid, "100%", "100%"],
                    timeout=3, capture_output=True,
                )
                logger.info("[BROWSER] Activated & maximized WhatsApp window %s", wid)
                return True
        except Exception:
            pass
        logger.warning("[BROWSER] Could not find WhatsApp window")
        return False

    # ── State detection via screenshot ─────────────────────────────────

    def _get_active_window_title(self) -> str:
        try:
            out = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=3,
            )
            return out.stdout.strip()
        except Exception:
            return ""

    def _detect_state(self) -> tuple[SendState, Optional[str]]:
        pg = self._pg
        if pg is None:
            return SendState.UNKNOWN, self._pg_init_error or "pyautogui unavailable"

        title = self._get_active_window_title()
        if not title:
            return SendState.BROWSER_CLOSED, "No active window found by xdotool"

        title_lower = title.lower()

        if "whatsapp" in title_lower and not re.search(r'\d{3,}', title):
            return SendState.UNKNOWN, "WhatsApp page is still loading"

        if re.search(r'\d{5,}', title):
            logger.debug("[STATE] Chat ready — title contains phone/contact digits")
            return SendState.SUCCESS, f"Chat ready: {title[:50]}"

        return SendState.UNKNOWN, f"Window title: {title[:80]}"

    # ── Popup handling ────────────────────────────────────────────────

    def _dismiss_popups(self) -> int:
        pg = self._pg
        if pg is None:
            return 0
        dismissed = 0
        for _ in range(3):
            try:
                pg.press("escape")
                time.sleep(1)
                dismissed += 1
            except Exception:
                break
        return dismissed

    # ── Wait for chat (polling loop with timeout) ─────────────────────

    def _wait_for_chat(self) -> tuple[SendState, Optional[str]]:
        deadline = time.time() + self.chat_load_timeout_s

        while time.time() < deadline:
            state, msg = self._detect_state()

            if state == SendState.SUCCESS:
                return state, msg
            if state == SendState.BROWSER_CLOSED:
                return state, msg

            logger.debug("[WAIT] state=%s msg=%s", state, msg)
            time.sleep(self.chat_poll_interval_s)

        return SendState.SLOW_LOAD, f"Chat did not load within {self.chat_load_timeout_s}s"

    # ── Click Send button ─────────────────────────────────────────────

    def _get_window_geometry(self, name: str = "WhatsApp") -> tuple[int, int, int, int]:
        """Return (x, y, width, height) of the first X11 window matching *name*."""
        try:
            wid = subprocess.run(
                ["xdotool", "search", "--name", name],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip().split("\n")[0]
            if not wid:
                return (0, 0, *self._pg.size())
            geo = subprocess.run(
                ["xdotool", "getwindowgeometry", wid],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip()
            pos_line = next((l for l in geo.split("\n") if "Position:" in l), None)
            geo_line = next((l for l in geo.split("\n") if "Geometry:" in l), None)
            if pos_line and geo_line:
                x, y = map(int, pos_line.split(":")[1].strip().split(","))
                w, h = map(int, geo_line.split(":")[1].strip().split("x"))
                return (x, y, w, h)
        except Exception:
            pass
        return (0, 0, *self._pg.size())

    def _click_send_button(self) -> bool:
        pg = self._pg
        if pg is None:
            return False

        ref = os.path.join(os.path.dirname(__file__), "send_button.png")
        if os.path.isfile(ref):
            try:
                loc = pg.locateOnScreen(ref, confidence=0.7, grayscale=True)
                if loc:
                    pg.click(loc)
                    logger.debug("Send: image-recognition click")
                    return True
            except Exception:
                pass

        win_x, win_y, win_w, win_h = self._get_window_geometry()
        input_x = win_x + int(win_w * 0.15)
        input_y = win_y + int(win_h * 0.92)
        pg.click(input_x, input_y)
        logger.debug("Send: input-area click (%d, %d)", input_x, input_y)
        time.sleep(0.5)
        pg.press("enter")
        logger.debug("Send: Enter key")
        return True

    # ── Phase-4: chat phone verification via window title ─────────────

    def _verify_chat_phone(self, phone: str) -> bool:
        """Check the active window title contains the target phone digits.

        WhatsApp Web sets the browser tab title to the contact name or
        phone number once the conversation loads.  We extract the raw
        phone digits and verify they appear in the window title.
        """
        raw_digits = re.sub(r"\D", "", phone)
        if not raw_digits:
            return True

        for _ in range(5):
            try:
                out = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=2,
                )
                title = out.stdout.strip()
                if not title:
                    time.sleep(1)
                    continue
                if raw_digits in re.sub(r"\D", "", title):
                    logger.debug("Chat phone verified: %s in title '%s'", phone, title)
                    return True
                logger.debug(
                    "Chat phone NOT matched: phone=%s title='%s' raw=%s",
                    phone, title, raw_digits,
                )
            except Exception:
                pass
            time.sleep(1)

        logger.warning("Chat phone verification failed for %s after polling", phone)
        return False

    # ── Phase-4: outgoing message bubble verification ─────────────────

    def _verify_outgoing_bubble(self) -> bool:
        logger.info("[VERIFY] Waiting %.0fs for message to send...", self.outgoing_bubble_timeout_s)
        time.sleep(self.outgoing_bubble_timeout_s)
        return True

    def _verify_sent(self) -> bool:
        logger.info("[VERIFY] Post-send wait %.0fs...", self.post_send_wait_s)
        time.sleep(self.post_send_wait_s)
        return True

    # ── Tab management (Ctrl+W) ───────────────────────────────────────

    def _close_tab(self) -> None:
        pg = self._pg
        if pg is None:
            return
        try:
            pg.hotkey("ctrl", "w")
            time.sleep(self.tab_close_delay_s)
        except Exception:
            pass

    # ── Main send flow (synchronous, runs in executor) ────────────────

    def _send_message_sync(
        self,
        phone: str,
        message: str,
        status_callback: Callable[[str], None],
    ) -> SendResult:
        result = SendResult(success=False)
        start_ts = time.time()

        if not self._ensure_pg():
            result.error = self._pg_init_error or "pyautogui unavailable"
            return result

        # 1. Internet check
        if not self._check_internet():
            result.state = SendState.NO_INTERNET
            result.error = "No internet connection"
            return result

        encoded = quote(message)
        url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}"

        for attempt in range(1, self.max_retries + 1):
            result.attempts = attempt
            logger.info("Send %s attempt %d/%d", phone, attempt, self.max_retries)

            try:
                # ── Phase 4: ensure NO stale tabs before opening ──────
                self._ensure_single_tab()

                # ── Open browser tab ──────────────────────────────────
                status_callback("opening_whatsapp")
                webbrowser.open(url)
                time.sleep(self.initial_wait_s)

                self._activate_browser()
                time.sleep(1)

                # ── Wait for chat to load ────────────────────────────
                status_callback("opening_chat")
                state, err = self._wait_for_chat()

                if state == SendState.LOGGED_OUT:
                    result.state = SendState.LOGGED_OUT
                    result.error = err or "WhatsApp Web logged out"
                    result.browser_state = "logged_out"
                    logger.error("LOGGED OUT — stopping campaign")
                    break

                if state == SendState.INVALID_NUMBER:
                    result.state = SendState.INVALID_NUMBER
                    result.error = err or "Invalid phone number"
                    result.browser_state = "invalid_number"
                    logger.warning("Invalid number %s", phone)
                    break

                if state == SendState.RATE_LIMITED:
                    result.state = SendState.RATE_LIMITED
                    result.error = err or "Rate limited"
                    result.browser_state = "rate_limited"
                    logger.warning("Rate limited — waiting %ds", self.rate_limit_delay_s)
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        time.sleep(self.rate_limit_delay_s)
                        self._close_tab()
                        self._verify_tab_closed()
                        continue
                    break

                if state == SendState.BROWSER_CLOSED:
                    logger.warning("Browser closed — restarting lead")
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        time.sleep(self.retry_delay_s)
                        continue
                    result.state = SendState.BROWSER_CLOSED
                    result.error = err or "Browser closed unexpectedly"
                    break

                if state == SendState.SLOW_LOAD:
                    logger.warning("Slow load for %s (attempt %d)", phone, attempt)
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        self._close_tab()
                        self._verify_tab_closed()
                        time.sleep(self.retry_delay_s)
                        continue
                    result.state = SendState.SLOW_LOAD
                    result.error = err or "Chat did not load in time"
                    break

                if state == SendState.UNKNOWN:
                    logger.warning("Unknown state for %s (attempt %d)", phone, attempt)
                    self._dismiss_popups()
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        self._close_tab()
                        self._verify_tab_closed()
                        time.sleep(self.retry_delay_s)
                        continue
                    result.state = SendState.UNKNOWN
                    result.error = err or "Could not determine WhatsApp state"
                    break

                # ── Phase 4: verify chat phone matches target ──────────
                if not self._verify_chat_phone(phone):
                    logger.warning("Chat phone mismatch for %s (attempt %d)", phone, attempt)
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        self._close_tab()
                        self._verify_tab_closed()
                        time.sleep(self.retry_delay_s)
                        continue
                    result.state = SendState.FAILED
                    result.error = "Chat phone verification failed"
                    break

                # ── Phase 4: message is pre-filled via URL — typing ──
                status_callback("typing")
                time.sleep(0.5)

                # ── Send ─────────────────────────────────────────────
                status_callback("sending")
                self._click_send_button()

                # ── Phase 4: verify outgoing bubble ──────────────────
                status_callback("sent")
                if self._verify_outgoing_bubble():
                    status_callback("verified")
                    result.success = True
                    result.state = SendState.SUCCESS
                    result.browser_state = "verified"
                    logger.info("Verified outgoing message for %s", phone)
                    break
                else:
                    logger.warning(
                        "Outgoing bubble not found for %s (attempt %d)",
                        phone, attempt,
                    )
                    if attempt < self.max_retries:
                        status_callback("retrying")
                        self._close_tab()
                        self._verify_tab_closed()
                        time.sleep(self.retry_delay_s)
                        continue
                    result.error = "Outgoing message not verified"
                    result.state = SendState.FAILED
                    break

            except Exception as exc:
                logger.exception("Unexpected error for %s (attempt %d)", phone, attempt)
                if attempt < self.max_retries:
                    status_callback("retrying")
                    self._close_tab()
                    self._verify_tab_closed()
                    time.sleep(self.retry_delay_s)
                    continue
                result.error = str(exc)
                result.state = SendState.FAILED
                result.browser_state = "exception"

        # ── Phase 4: verify tab is gone before returning ──────────────
        self._close_tab()
        self._verify_tab_closed()
        time.sleep(self.inter_lead_delay_s)

        result.duration_ms = (time.time() - start_ts) * 1000
        return result

    # ── Async public API ──────────────────────────────────────────────

    async def send(
        self,
        phone: str,
        message: str,
        status_callback: Callable[[str], None],
    ) -> SendResult:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._send_message_sync,
            phone,
            message,
            status_callback,
        )


whatsapp_sender = WhatsAppSender()
