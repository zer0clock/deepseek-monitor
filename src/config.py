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


def save_config(cfg: Config) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps(asdict(cfg), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.debug("Config saved to %s", CONFIG_FILE)
