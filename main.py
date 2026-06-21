#!/usr/bin/env python3
"""
DeepSeek Monitor — Balance display + taskbar widget.

Usage:
    python main.py
    DEEPSEEK_API_KEY=sk-xxx python main.py
"""

import ctypes
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


# ══════════════════════════════════════════════════════════════════════════════
#  Single-instance check (Windows mutex)
# ══════════════════════════════════════════════════════════════════════════════

MUTEX_NAME = "Global\\DeepSeekMonitor_SingleInstance"


def _ensure_single_instance() -> bool:
    """Return True if this is the first instance."""
    if sys.platform != "win32":
        return True

    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    ERROR_ALREADY_EXISTS = 183
    SW_RESTORE = 9

    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if kernel32.GetLastError() != ERROR_ALREADY_EXISTS:
        return True

    # Find existing window and bring to front
    hwnd = user32.FindWindowW(None, "DeepSeek Monitor")
    if hwnd:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.SetForegroundWindow(hwnd)
        current_thread = kernel32.GetCurrentThreadId()
        foreground_thread = user32.GetWindowThreadProcessId(
            user32.GetForegroundWindow(), None
        )
        if current_thread != foreground_thread:
            user32.AttachThreadInput(current_thread, foreground_thread, True, 0)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(current_thread, foreground_thread, False, 0)

    logging.info("Another instance is already running — exiting")
    return False


def _setup_logging():
    """Configure logging to file and stderr."""
    log_dir = Path.home() / ".deepseek-monitor"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "deepseek-monitor.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("DeepSeek Monitor starting — log: %s", log_file)


def main():
    missing = []
    try:
        import PIL  # noqa
    except ImportError:
        missing.append("Pillow")
    if missing:
        logging.warning(
            "Pillow not found — install with: pip install Pillow  "
            "(icon generation will use fallback)"
        )

    from src.app import DeepSeekMonitorApp
    DeepSeekMonitorApp.run()


if __name__ == "__main__":
    _setup_logging()
    if not _ensure_single_instance():
        sys.exit(0)
    main()
