"""Configuration manager."""

import json
import logging
import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".deepseek-monitor"
CONFIG_FILE = DATA_DIR / "config.json"


@dataclass
class Config:
    api_key: str = ""
    refresh_interval: int = 60
    language: str = "zh"
    minimize_to_tray: bool = True
    show_taskbar_widget: bool = True
    taskbar_widget_position: str = "right"
    win_x: Optional[int] = None
    win_y: Optional[int] = None
    # Taskbar widget balance colors (RGB hex strings)
    tw_color_high: str = "#99FF66"   # balance > threshold_high  — green
    tw_color_mid:  str = "#FFD66D"   # threshold_low < balance ≤ threshold_high
    tw_color_low:  str = "#FF6666"   # balance ≤ threshold_low   — red
    tw_color_label: str = "#808080"  # label text                — gray
    # Balance thresholds
    tw_threshold_high: float = 20.0
    tw_threshold_low:  float = 5.0


def load_config() -> Config:
    cfg = Config()
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            valid_keys = {k for k in data if k in Config.__dataclass_fields__}
            cfg = Config(**{k: data[k] for k in valid_keys})
        except (json.JSONDecodeError, TypeError, KeyError, OSError) as e:
            logger.warning("Failed to load config from %s: %s — using defaults",
                           CONFIG_FILE, e)
        except Exception:
            logger.exception("Unexpected error loading config — using defaults")
    else:
        logger.info("No config file found at %s — using defaults", CONFIG_FILE)

    env_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if env_key and not cfg.api_key:
        cfg.api_key = env_key
        logger.info("Using API key from DEEPSEEK_API_KEY environment variable")
    return cfg


def rgb_to_bgr(hex_color: str) -> int:
    """Convert RGB hex string '#RRGGBB' to BGR integer for Win32 GDI."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


def bgr_to_rgb(bgr: int) -> str:
    """Convert BGR integer to RGB hex string '#RRGGBB'."""
    b = (bgr >> 16) & 0xFF
    g = (bgr >> 8) & 0xFF
    r = bgr & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def save_config(cfg: Config) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("Config saved to %s", CONFIG_FILE)
