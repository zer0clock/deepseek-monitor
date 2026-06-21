"""Configuration manager."""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

DATA_DIR = Path.home() / ".deepseek-monitor"
CONFIG_FILE = DATA_DIR / "config.json"

# Layered balance history files
HIST_FILES = {
    "day":     DATA_DIR / "balance_history_day.json",
    "week":    DATA_DIR / "balance_history_week.json",
    "month":   DATA_DIR / "balance_history_month.json",
    "quarter": DATA_DIR / "balance_history_quarter.json",
    "year":    DATA_DIR / "balance_history_year.json",
}

_RANGE_DAYS = {"day": 1, "week": 7, "month": 30, "quarter": 90, "year": 365}


def _load_json(path: Path) -> list:
    """Load a JSON list from path, return [] on any failure."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path.name, e)
        return []


def _save_json(path: Path, data: list) -> None:
    """Save a list to a JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_history(range_key: str) -> list:
    """Load balance history for a given time range (day/week/month/quarter/year)."""
    return _load_json(HIST_FILES.get(range_key, HIST_FILES["month"]))


def append_history_record(record: dict) -> None:
    """Append a single raw record to the day file."""
    day_data = _load_json(HIST_FILES["day"])
    day_data.append(record)
    _save_json(HIST_FILES["day"], day_data)


def compact_all() -> None:
    """Rebuild all layered history files from the raw day data.

    Should be called on app startup and daily at 00:01.
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # --- Day: keep only today's records ---
    day_data = _load_json(HIST_FILES["day"])
    day_data = [r for r in day_data if r.get("ts", "").startswith(today_str)]
    _save_json(HIST_FILES["day"], day_data)

    # --- Week: aggregate by hour (last 7 days) ---
    cutoff = now - timedelta(days=7)
    week_data = _load_json(HIST_FILES["week"])
    all_points = _merge_sources(day_data, week_data, cutoff=cutoff)
    _save_json(HIST_FILES["week"], _aggregate(all_points, "hour"))

    # --- Month: aggregate by day (last 30 days) ---
    cutoff = now - timedelta(days=30)
    month_data = _load_json(HIST_FILES["month"])
    # Use day data (today) + existing month data
    all_points = _merge_sources(day_data, month_data, cutoff=cutoff)
    _save_json(HIST_FILES["month"], _aggregate(all_points, "day"))

    # --- Quarter: aggregate by day (last 90 days) ---
    cutoff = now - timedelta(days=90)
    quarter_data = _load_json(HIST_FILES["quarter"])
    all_points = _merge_sources(day_data, quarter_data, cutoff=cutoff)
    _save_json(HIST_FILES["quarter"], _aggregate(all_points, "day"))

    # --- Year: aggregate by week (last 365 days) ---
    cutoff = now - timedelta(days=365)
    year_data = _load_json(HIST_FILES["year"])
    all_points = _merge_sources(day_data, year_data, cutoff=cutoff)
    _save_json(HIST_FILES["year"], _aggregate(all_points, "week"))

    logger.info("History compacted at %s", now.isoformat())


def _merge_sources(*sources: list, cutoff: datetime) -> list:
    """Merge multiple lists of records, deduplicate by ts, filter by cutoff."""
    from datetime import datetime as dt
    seen = set()
    merged = []
    ts_key = "ts"
    for src in sources:
        for r in src:
            k = r.get(ts_key, "")
            if k in seen:
                continue
            seen.add(k)
            try:
                if dt.fromisoformat(k) >= cutoff:
                    merged.append(r)
            except (ValueError, TypeError):
                pass
    merged.sort(key=lambda r: r.get(ts_key, ""))
    return merged


def _aggregate(points: list, level: str) -> list:
    """Aggregate data points by time bucket (hour/day/week).

    Returns list of {ts, total, granted, topup, currency, count}.
    """
    from datetime import datetime as dt, timedelta

    if not points:
        return []

    def bucket_key(r):
        ts = dt.fromisoformat(r["ts"])
        if level == "hour":
            return ts.strftime("%Y-%m-%dT%H:00")
        elif level == "week":
            # ISO week start (Monday)
            weekday = ts.weekday()
            week_start = ts - timedelta(days=weekday)
            return week_start.strftime("%Y-%m-%d") + " (week)"
        else:  # day
            return ts.strftime("%Y-%m-%d")

    buckets = {}
    for r in points:
        k = bucket_key(r)
        if k not in buckets:
            buckets[k] = {"total": 0, "granted": 0, "topup": 0, "count": 0,
                          "currency": r.get("currency", "CNY")}
        b = buckets[k]
        w = r.get("count", 1)
        b["total"] += r["total"] * w
        b["granted"] += r.get("granted", 0) * w
        b["topup"] += r.get("topup", 0) * w
        b["count"] += w

    result = []
    for k in sorted(buckets.keys()):
        b = buckets[k]
        total_w = b["count"] or 1
        result.append({
            "ts": k,
            "total": round(b["total"] / total_w, 6),
            "granted": round(b["granted"] / total_w, 6),
            "topup": round(b["topup"] / total_w, 6),
            "currency": b["currency"],
            "count": b["count"],
        })
    return result


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
    # Auto-start with Windows
    auto_start: bool = False


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
