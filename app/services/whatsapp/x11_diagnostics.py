"""X11/DISPLAY diagnostic utility for PyAutoGUI initialization."""

import logging
import os
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class X11Diagnostics:
    """Comprehensive X11/DISPLAY diagnostic utility for PyAutoGUI."""

    @staticmethod
    def get_current_user() -> str:
        """Get the current user running the process."""
        try:
            return subprocess.run(
                ["whoami"],
                capture_output=True,
                text=True,
                timeout=2
            ).stdout.strip()
        except Exception as e:
            logger.error("[X11] Failed to get current user: %s", e)
            return "unknown"

    @staticmethod
    def get_display() -> Optional[str]:
        """Get and validate DISPLAY environment variable."""
        display = os.environ.get('DISPLAY')
        if display:
            logger.info("[X11] DISPLAY is set: %s", display)
        else:
            logger.error("[X11] DISPLAY environment variable NOT set")
        return display

    @staticmethod
    def get_xauthority() -> Optional[str]:
        """Get XAUTHORITY path, using ``xauth info`` as the source of truth.

        The Python process ``os.environ`` may be missing ``XAUTHORITY`` even
        when the **shell** has it.  ``xauth info`` always reports the real
        path because it inherits the shell environment.  If that fails,
        fall back to the environment variable and ``~/.Xauthority``.
        """
        try:
            r = subprocess.run(
                ["xauth", "info"],
                capture_output=True, text=True, timeout=3,
            )
            for line in r.stdout.split("\n"):
                if "Authority file" in line:
                    path = line.split(":", 1)[-1].strip()
                    if path and os.path.isfile(path):
                        logger.info("[X11] XAUTHORITY from xauth info: %s", path)
                        return path
        except Exception as e:
            logger.debug("[X11] xauth info failed: %s", e)

        xauth = os.environ.get('XAUTHORITY')
        if xauth:
            if os.path.isfile(xauth):
                logger.info("[X11] XAUTHORITY file exists: %s", xauth)
                return xauth
            logger.warning("[X11] XAUTHORITY set but file not found: %s", xauth)

        home = os.path.expanduser("~")
        default_xauth = os.path.join(home, ".Xauthority")
        if os.path.isfile(default_xauth):
            logger.info("[X11] Using default .Xauthority: %s", default_xauth)
            return default_xauth

        logger.error("[X11] No XAUTHORITY file found")
        return None

    @staticmethod
    def check_xauthority_permissions() -> bool:
        """Verify .Xauthority file has correct permissions (600)."""
        xauth = X11Diagnostics.get_xauthority()
        if not xauth:
            return False
        
        try:
            stat_result = os.stat(xauth)
            mode = oct(stat_result.st_mode)[-3:]
            logger.info("[X11] .Xauthority permissions: %s", mode)
            if mode != "600":
                logger.warning("[X11] Permissions not 600 (found: %s), fixing...", mode)
                os.chmod(xauth, 0o600)
                logger.info("[X11] Fixed permissions to 600")
                return True
            return True
        except PermissionError:
            logger.error("[X11] Permission denied checking/fixing .Xauthority")
            return False
        except Exception as e:
            logger.error("[X11] Failed to check permissions: %s", e)
            return False

    @staticmethod
    def test_x11_connection(display: Optional[str]) -> Tuple[bool, str]:
        """Test connection to X11 display using xset."""
        if not display:
            return False, "DISPLAY not set"
        
        try:
            env = {**os.environ, 'DISPLAY': display}
            result = subprocess.run(
                ['xset', 'q'],
                env=env,
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                logger.info("[X11] X11 connection test PASSED for display %s", display)
                return True, "X11 connection successful"
            else:
                error_msg = (result.stderr or result.stdout).strip()
                logger.error("[X11] X11 test failed: %s", error_msg)
                return False, error_msg
        except FileNotFoundError:
            logger.warning("[X11] xset command not found, trying alternative check...")
            return X11Diagnostics._fallback_x11_check(display)
        except subprocess.TimeoutExpired:
            logger.error("[X11] X11 connection test timeout")
            return False, "X11 connection test timeout"
        except Exception as e:
            logger.error("[X11] X11 connection test error: %s", e)
            return False, str(e)

    @staticmethod
    def _fallback_x11_check(display: Optional[str]) -> Tuple[bool, str]:
        """Fallback X11 check without xset using xrandr or xlsclients."""
        if not display:
            return False, "DISPLAY not set"
        
        try:
            env = {**os.environ, 'DISPLAY': display}
            # Try xlsclients
            result = subprocess.run(
                ['xlsclients'],
                env=env,
                capture_output=True,
                timeout=3,
                text=True
            )
            if result.returncode == 0:
                logger.info("[X11] Fallback X11 check PASSED using xlsclients")
                return True, "X11 connection successful (xlsclients)"
            else:
                logger.warning("[X11] xlsclients failed, trying xrandr...")
                # Try xrandr
                result = subprocess.run(
                    ['xrandr', '--list-outputs'],
                    env=env,
                    capture_output=True,
                    timeout=3,
                    text=True
                )
                if result.returncode == 0:
                    logger.info("[X11] Fallback X11 check PASSED using xrandr")
                    return True, "X11 connection successful (xrandr)"
                return False, "All fallback checks failed"
        except Exception as e:
            return False, f"Fallback checks failed: {e}"

    @staticmethod
    def run_full_diagnostics() -> dict:
        """Run comprehensive diagnostics and return results."""
        diagnostics = {
            "current_user": X11Diagnostics.get_current_user(),
            "display": X11Diagnostics.get_display(),
            "xauthority": X11Diagnostics.get_xauthority(),
            "xauthority_permissions_ok": False,
            "x11_connection_ok": False,
            "x11_connection_error": None,
        }
        
        # Check permissions (this also fixes them if needed)
        if diagnostics["xauthority"]:
            diagnostics["xauthority_permissions_ok"] = X11Diagnostics.check_xauthority_permissions()
        
        # Test X11 connection
        display = diagnostics["display"]
        if display:
            ok, msg = X11Diagnostics.test_x11_connection(display)
            diagnostics["x11_connection_ok"] = ok
            diagnostics["x11_connection_error"] = msg
        
        return diagnostics

    @staticmethod
    def log_diagnostics(diagnostics: dict) -> None:
        """Log diagnostics in structured format."""
        logger.info("=" * 70)
        logger.info("[X11DIAG] X11/DISPLAY Diagnostics Report")
        logger.info("=" * 70)
        logger.info("[X11DIAG] Current User:           %s", diagnostics.get("current_user", "unknown"))
        logger.info("[X11DIAG] DISPLAY:                 %s", diagnostics.get("display") or "NOT SET")
        logger.info("[X11DIAG] XAUTHORITY:              %s", diagnostics.get("xauthority") or "NOT FOUND")
        logger.info("[X11DIAG] XAUTHORITY Permissions:  %s", "✓ OK" if diagnostics.get("xauthority_permissions_ok") else "✗ FAILED")
        logger.info("[X11DIAG] X11 Connection:          %s", "✓ PASSED" if diagnostics.get("x11_connection_ok") else "✗ FAILED")
        if diagnostics.get("x11_connection_error"):
            logger.error("[X11DIAG] Error Details:            %s", diagnostics["x11_connection_error"])
        logger.info("=" * 70)

    @staticmethod
    def get_remediation_steps(diagnostics: dict) -> list:
        """Generate actionable remediation steps."""
        steps = []
        
        if not diagnostics.get("display"):
            steps.append("1. Set DISPLAY: export DISPLAY=:0")
            steps.append("2. Or from SSH: ssh -X user@host")
            steps.append("3. In systemd service add: Environment=\"DISPLAY=:0\" Environment=\"XAUTHORITY=/home/user/.Xauthority\"")
            steps.append("4. In Docker: docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ...")
        
        if not diagnostics.get("xauthority"):
            steps.append("1. Check X session: grep -r XAUTHORITY /proc/[pid of X session]/environ | head -1")
            steps.append("2. Grant access: xhost +local: (run in active X session)")
            steps.append("3. Export from active session: xauth list > /tmp/xauth_export")
            steps.append("4. Import in new context: xauth merge /tmp/xauth_export")
        
        if not diagnostics.get("xauthority_permissions_ok"):
            steps.append("1. Fix permissions: chmod 600 ~/.Xauthority")
        
        if not diagnostics.get("x11_connection_ok"):
            steps.append("1. Verify X server running: ps aux | grep X")
            steps.append("2. Check DISPLAY is correct: echo $DISPLAY (from X session)")
            steps.append("3. Grant access: xhost +local: (run in active X session)")
            steps.append("4. Verify same user: whoami (both sessions)")
        
        return steps

    @staticmethod
    def log_remediation(diagnostics: dict) -> None:
        """Log remediation steps."""
        steps = X11Diagnostics.get_remediation_steps(diagnostics)
        if steps:
            logger.error("[X11REM] Remediation steps:")
            for step in steps:
                logger.error("[X11REM] %s", step)
