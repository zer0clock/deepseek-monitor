"""
DeepSeek Monitor — Balance-only desktop app with taskbar widget.

Features:
  - Balance display (GET /user/balance)
  - Taskbar embedded widget (LiteMonitor style)
  - System tray icon
  - Configurable refresh interval
  - Chinese / English language toggle
"""

import logging
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict

import tkinter as tk
from tkinter import ttk, messagebox, colorchooser

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Resolve bundled assets path (works in PyInstaller and development)
if getattr(sys, "frozen", False):
    BASE_PATH = Path(sys._MEIPASS)
else:
    BASE_PATH = Path(__file__).resolve().parent.parent

from src.config import (Config, load_config, save_config, DATA_DIR,
                         load_history, append_history_record, compact_all,
                         rgb_to_bgr)
from src.api import DeepSeekClient, DeepSeekAPIError

logger = logging.getLogger(__name__)

try:
    from src.taskbar_widget import TaskbarWidget
    HAS_TW = sys.platform == "win32"
except Exception:
    HAS_TW = False
    logger.warning("Failed to import TaskbarWidget:\n%s", traceback.format_exc())

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ══════════════════════════════════════════════════════════════════════════════
#  I18N
# ══════════════════════════════════════════════════════════════════════════════

T = {
    "en": {
        "title":        "💰 DeepSeek Monitor",
        "balance":      "Balance",
        "status":       "Status",
        "available":    "✅ Available",
        "insufficient": "❌ Insufficient",
        "granted":      "Granted",
        "topup":        "Top-up",
        "refresh":      "🔄 Refresh",
        "last_update":  "Last updated",
        "fetching":     "⏳ Fetching...",
        "tab_overview":  "📊 Overview",
        "tab_settings":  "⚙ Settings",
        "api_key":       "🔑 API Key",
        "api_key_hint":  "Stored locally, never shared.",
        "save_key":      "Save Key",
        "refresh_int":   "⏱ Refresh Interval",
        "refresh_hint":  "How often to poll the balance API",
        "taskbar_wid":   "📌 Taskbar Widget",
        "taskbar_hint":   "Show balance directly on Windows taskbar",
        "balance_colors": "Balance colors:",
        "thresholds":     "Thresholds:",
        "enable":         "Enable",
        "position":      "Position",
        "right":         "Right",
        "left":          "Left",
        "language":      "🌐 Language",
        "about":         "ℹ About",
        "about_text":    "DeepSeek Monitor v2.0\n"
                         "Lightweight Windows tool for monitoring DeepSeek API balance.\n\n"
                         "• Data: DeepSeek API (GET /user/balance)\n"
                         "• Set DEEPSEEK_API_KEY env var for auto-login",
        "login_title":   "Login — DeepSeek API Key",
        "enter_key":     "🔑 Enter your DeepSeek API Key",
        "login":         "Login",
        "cancel":        "Cancel",
        "key_empty":     "Please enter your API key.",
        "key_saved":     "API key saved. Refreshing...",
        "no_key":        "No API key configured",
        "balance_info":  "Total Balance",
        "no_data":       "No balance info",
        "pricing_title": "💰 Model Pricing (CNY / 1M tokens)",
        "pricing_text":  "  Model              Input    Output   Cache Hit\n"
                         "  ────────────────────────────────────────────\n"
                         "  deepseek-v4-pro    ¥3.00    ¥6.00    ¥0.025\n"
                         "  deepseek-v4-flash  ¥1.00    ¥2.00    ¥0.02",
        "confirm_clr":    "Clear all local data?",
        "btn_exit":       "Exit",
        "btn_show":       "Show Window",
        "btn_ref_now":    "Refresh Now",
        "tray_msg":       "Running in background. Double-click tray icon to open.",
        "auto_start":      "Auto-start with Windows",
        "tab_history":     "📊 Spending",
        "range_day":       "Day",
        "range_week":      "Week",
        "range_month":     "Month",
        "range_quarter":   "Qtr",
        "range_year":      "Year",
        "history_start":   "Start",
        "history_current": "Current",
        "history_change":  "Change",
        "history_no_data": "No data yet",
    },
    "zh": {
        "title":        "💰 DeepSeek 余额监控",
        "balance":      "余额",
        "status":       "状态",
        "available":    "✅ 可用",
        "insufficient": "❌ 不足",
        "granted":      "赠送余额",
        "topup":        "充值余额",
        "refresh":      "🔄 刷新",
        "last_update":  "上次更新",
        "fetching":     "⏳ 获取中...",
        "tab_overview":  "📊 概览",
        "tab_settings":  "⚙ 设置",
        "api_key":       "🔑 API Key",
        "api_key_hint":  "仅保存在本地，不会发送给第三方。",
        "save_key":      "保存",
        "refresh_int":   "⏱ 刷新间隔",
        "refresh_hint":  "自动轮询余额 API 的频率",
        "taskbar_wid":   "📌 任务栏小组件",
        "taskbar_hint":   "在 Windows 任务栏上直接显示余额",
        "balance_colors": "余额颜色：",
        "thresholds":     "阈值：",
        "enable":         "启用",
        "position":      "位置",
        "right":         "右侧",
        "left":          "左侧",
        "language":      "🌐 语言",
        "about":         "ℹ 关于",
        "about_text":    "DeepSeek 余额监控 v2.0\n"
                         "轻量级 Windows 余额查询工具。\n\n"
                         "• 数据来源：DeepSeek API (GET /user/balance)\n"
                         "• 设置环境变量 DEEPSEEK_API_KEY 自动登录",
        "login_title":   "登录 — DeepSeek API Key",
        "enter_key":     "🔑 请输入 DeepSeek API Key",
        "login":         "登录",
        "cancel":        "取消",
        "key_empty":     "请输入 API Key。",
        "key_saved":     "已保存，正在刷新...",
        "no_key":        "未配置 API Key",
        "balance_info":  "总余额",
        "no_data":       "暂无余额信息",
        "pricing_title": "💰 模型定价 (CNY / 1M tokens)",
        "pricing_text":  "  Model              Input    Output   Cache Hit\n"
                         "  ────────────────────────────────────────────\n"
                         "  deepseek-v4-pro    ¥3.00    ¥6.00    ¥0.025\n"
                         "  deepseek-v4-flash  ¥1.00    ¥2.00    ¥0.02",
        "confirm_clr":    "确定清除所有本地数据？",
        "btn_exit":       "退出",
        "btn_show":       "显示窗口",
        "btn_ref_now":    "立即刷新",
        "tray_msg":       "已最小化到后台，双击托盘图标打开。",
        "auto_start":      "开机自启",
        "tab_history":     "📊 花费曲线",
        "range_day":       "日",
        "range_week":      "周",
        "range_month":     "月",
        "range_quarter":   "季度",
        "range_year":      "年",
        "history_start":   "起始",
        "history_current": "当前",
        "history_change":  "变化",
        "history_no_data": "暂无数据",
    },
}


def t(key: str) -> str:
    """Get translated string."""
    lang = AppGlobals.lang
    return T.get(lang, T["en"]).get(key, key)


# ══════════════════════════════════════════════════════════════════════════════
#  Shared globals (accessible from anywhere)
# ══════════════════════════════════════════════════════════════════════════════

class AppGlobals:
    lang: str = "zh"  # default language


# ══════════════════════════════════════════════════════════════════════════════
#  Theme & Fonts
# ══════════════════════════════════════════════════════════════════════════════

C = {
    "bg": "#1e1e2e", "bg2": "#282840", "bg3": "#313150",
    "accent": "#89b4fa", "green": "#a6e3a1", "red": "#f38ba8",
    "yellow": "#f9e2af", "text": "#cdd6f4", "text2": "#a6adc8",
    "border": "#45475a", "header": "#181825",
    "btn": "#3b3b5c", "btn_h": "#4a4a6e",
}

F = {
    "title": ("Segoe UI", 22, "bold"), "bal": ("Consolas", 36, "bold"),
    "sec": ("Segoe UI", 13, "bold"), "body": ("Segoe UI", 10),
    "small": ("Segoe UI", 9), "mono": ("Consolas", 10),
    "tab": ("Segoe UI", 10),
}


# ══════════════════════════════════════════════════════════════════════════════
#  Icon generation
# ══════════════════════════════════════════════════════════════════════════════

def create_icon(path: Path, size: int = 64) -> bool:
    if not HAS_PIL: return False
    try:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, size-2, size-2], fill="#89b4fa", outline="#585b70", width=2)
        try: font = ImageFont.truetype("arial.ttf", int(size * 0.55))
        except: font = ImageFont.load_default()
        bb = d.textbbox((0, 0), "$", font=font)
        tw, th = bb[2]-bb[0], bb[3]-bb[1]
        d.text(((size-tw)/2, (size-th)/2-2), "$", fill="#1e1e2e", font=font)
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path))
        return True
    except: return False


# ══════════════════════════════════════════════════════════════════════════════
#  Balance formatting helper
# ══════════════════════════════════════════════════════════════════════════════

def _currency_symbol(currency: Optional[str]) -> str:
    """Return the appropriate currency symbol for a DeepSeek currency code."""
    if currency == "USD":
        return "$"
    elif currency == "CNY":
        return "¥"
    elif currency:
        return currency  # fallback: show the code itself
    return "¥"


def _format_balance(data: Dict) -> Dict[str, str]:
    """Extract and format balance fields from API response.

    Returns a dict with keys: total, avail, granted, topup, error.
    Caller uses the dict to populate whichever UI labels are needed.
    """
    infos = data.get("balance_infos", [])
    if not infos:
        return {"error": t("no_data")}

    b = infos[0]
    total   = float(b.get("total_balance", 0))
    granted = float(b.get("granted_balance", 0))
    topped  = float(b.get("topped_up_balance", 0))
    sym     = _currency_symbol(b.get("currency"))
    avail   = data.get("is_available", False)

    return {
        "total":   f"{sym}{total:.2f}",
        "avail":   f"{t('status')}: {t('available') if avail else t('insufficient')}",
        "granted": f"{t('granted')}: {sym}{granted:.2f}",
        "topup":   f"{t('topup')}:  {sym}{topped:.2f}",
        "is_avail": avail,
        "total_raw": total,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Scrollable Frame helper
# ══════════════════════════════════════════════════════════════════════════════

class ScrollableFrame(ttk.Frame):
    """A frame with a vertical scrollbar for use inside Notebook tabs."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0,
                                bd=0, relief="flat")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview)
        self._content = ttk.Frame(self.canvas)

        self._content.bind("<Configure>",
                           lambda _: self.canvas.configure(
                               scrollregion=self.canvas.bbox("all")))

        self._canvas_window = self.canvas.create_window(
            (0, 0), window=self._content, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind canvas resize to re-center content width
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        # Mouse wheel scrolling
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    @property
    def content(self) -> ttk.Frame:
        return self._content

    def _on_canvas_resize(self, event):
        self.canvas.itemconfig(self._canvas_window, width=event.width)

    def _bind_mousewheel(self, _event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


# ══════════════════════════════════════════════════════════════════════════════
#  Balance Chart (tkinter Canvas)
# ══════════════════════════════════════════════════════════════════════════════

class BalanceChart(tk.Canvas):
    """A simple line chart for balance history drawn on a tkinter Canvas."""

    PAD_LEFT = 60
    PAD_RIGHT = 20
    PAD_TOP = 16
    PAD_BOTTOM = 36

    def __init__(self, parent, **kwargs):
        bg = kwargs.pop("bg", C["bg2"])
        super().__init__(parent, bg=bg, highlightthickness=0, bd=0, **kwargs)
        self._records = []
        self.bind("<Configure>", lambda _: self.draw())

    def set_data(self, records: list):
        """Set the data to display. Each record: {ts, total, granted, topup, currency}."""
        self._records = records or []
        self.draw()

    def draw(self):
        """Redraw the chart."""
        self.delete("all")
        if not self._records:
            self._draw_empty()
            return

        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        left = self.PAD_LEFT
        right = w - self.PAD_RIGHT
        top = self.PAD_TOP
        bottom = h - self.PAD_BOTTOM
        pw = right - left
        ph = bottom - top

        if pw < 20 or ph < 20:
            return

        totals = [r["total"] for r in self._records]
        y_min, y_max = min(totals), max(totals)
        if y_min == y_max:
            y_min -= abs(y_min) * 0.5 + 1
            y_max += abs(y_max) * 0.5 + 1
        margin = (y_max - y_min) * 0.10
        y_min -= margin
        y_max += margin
        if y_min < 0 and y_max > 0:
            y_min = min(y_min, -margin)

        # Grid + Y axis labels
        n_ticks = 5
        tick_step = (y_max - y_min) / (n_ticks - 1)
        for i in range(n_ticks):
            val = y_min + tick_step * i
            y = bottom - (val - y_min) / (y_max - y_min) * ph
            # Grid line
            self.create_line(left, y, right, y, fill=C["border"], dash=(3, 5))
            # Y label
            sym = self._records[0].get("currency", "CNY") if self._records else "CNY"
            sym = _currency_symbol(sym)
            self.create_text(left - 8, y, text=f"{sym}{val:.2f}",
                             fill=C["text2"], font=F["small"], anchor="e")

        n = len(self._records)
        # X axis labels
        x_labels = self._pick_x_labels(n)
        # Map data points
        points = []
        for i, r in enumerate(self._records):
            x = left + (i / max(n - 1, 1)) * pw
            y = bottom - (r["total"] - y_min) / (y_max - y_min) * ph
            points.append((x, y))
            # Draw dot
            if n <= 60 or i % max(1, n // 50) == 0:
                self.create_oval(x - 3, y - 3, x + 3, y + 3,
                                 fill=C["accent"], outline=C["bg2"], width=1)
            # X axis label
            if i in x_labels:
                ts = r["ts"]
                label = ts[11:16] if "T" in ts else ts[:10]  # HH:MM or YYYY-MM-DD
                self.create_text(x, bottom + 16, text=label,
                                 fill=C["text2"], font=F["small"], anchor="n")

        # Draw line
        if len(points) >= 2:
            flat = [c for p in points for c in p]
            self.create_line(*flat, fill=C["accent"], width=2, smooth=False, joinstyle="round")

        # Axis lines
        self.create_line(left, top, left, bottom, fill=C["border"])
        self.create_line(left, bottom, right, bottom, fill=C["border"])

    def _pick_x_labels(self, n: int) -> set:
        """Pick which data point indices get X-axis labels."""
        if n <= 8:
            return set(range(n))
        if n <= 30:
            step = max(1, n // 6)
            return set(range(0, n, step))
        step = max(1, n // 8)
        return set(range(0, n, step))

    def _draw_empty(self):
        self.create_text(
            self.winfo_width() / 2, self.winfo_height() / 2,
            text=t("history_no_data"), fill=C["text2"], font=F["body"],
        )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class DeepSeekMonitorApp:

    def __init__(self, root: tk.Tk, config: Config):
        self.root   = root
        self.config = config
        self.client: Optional[DeepSeekClient] = None
        self._timer = None
        self._busy  = False
        self._tray  = None
        self._tw: Optional[TaskbarWidget] = None
        self._last_data: Optional[Dict] = None
        # Store the real API key separately from the masked display
        self._stored_key: str = config.api_key

        AppGlobals.lang = config.language

        self._build_root()
        self._build_styles()
        self._build_ui()
        self._init_tray()
        self._init_taskbar()

        # Compact history on startup
        compact_all()
        self._last_history_date = datetime.now().strftime("%Y-%m-%d")
        self._schedule_midnight_compact()

        # Apply existing auto-start setting (ensures registry is correct)
        if self.config.auto_start:
            self._set_auto_start_registry(True)

        if self.config.api_key:
            self.root.after(300, self._refresh)
            self.root.after(600, self._schedule)
        else:
            self.root.after(200, self._login)

    # ── Root ──────────────────────────────────────────────────────────────────

    def _build_root(self):
        self.root.title("DeepSeek Monitor")
        self.root.configure(bg=C["bg"])
        self.root.minsize(800, 540)
        self.root.geometry("920x640")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.config.win_x is not None:
            self.root.geometry(f"+{self.config.win_x}+{self.config.win_y}")
        ico = BASE_PATH / "assets" / "favicon.ico"
        if ico.exists():
            try: self.root.iconbitmap(str(ico))
            except: pass

    def _build_styles(self):
        s = ttk.Style(); s.theme_use("clam")
        s.configure("TNotebook", background=C["bg"], borderwidth=0)
        s.configure("TNotebook.Tab", background=C["bg2"], foreground=C["text"],
                     padding=[16, 8], font=F["tab"])
        s.map("TNotebook.Tab",
              background=[("selected", C["accent"])], foreground=[("selected", C["bg"])])
        s.configure("TFrame", background=C["bg"])
        s.configure("H.TFrame", background=C["header"])
        s.configure("C.TFrame", background=C["bg2"])
        s.configure("TLabel", background=C["bg"], foreground=C["text"], font=F["body"])
        s.configure("H.TLabel", background=C["header"], foreground=C["text"], font=F["body"])
        s.configure("C.TLabel", background=C["bg2"], foreground=C["text"], font=F["body"])
        s.configure("Title.TLabel", background=C["header"], foreground=C["text"], font=F["title"])
        s.configure("Bal.TLabel", background=C["header"], foreground=C["green"], font=F["bal"])
        s.configure("Sec.TLabel", background=C["bg"], foreground=C["accent"], font=F["sec"])
        s.configure("Sm.TLabel", background=C["bg2"], foreground=C["text2"], font=F["small"])
        s.configure("Sm2.TLabel", background=C["header"], foreground=C["text2"], font=F["small"])
        s.configure("Mono.TLabel", background=C["bg2"], foreground=C["text"], font=F["mono"])
        s.configure("TButton", background=C["btn"], foreground=C["text"],
                     borderwidth=0, padding=[14, 6], font=F["body"])
        s.map("TButton", background=[("active", C["btn_h"])])
        s.configure("Acc.TButton", background=C["accent"], foreground=C["bg"])
        s.map("Acc.TButton", background=[("active", "#6fa0e8")])

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Header
        hdr = ttk.Frame(self.root, style="H.TFrame")
        hdr.pack(fill="x")
        hf = ttk.Frame(hdr, style="H.TFrame"); hf.pack(fill="x", padx=24, pady=(18, 10))
        self._lbl_title = ttk.Label(hf, text=t("title"), style="Title.TLabel")
        self._lbl_title.pack(side="left")
        self._lbl_status = ttk.Label(hf, text="", style="Sm2.TLabel")
        self._lbl_status.pack(side="right", padx=(0, 12))
        self._btn_refresh = ttk.Button(hf, text=t("refresh"), command=self._manual_refresh)
        self._btn_refresh.pack(side="right", padx=(0, 10))

        bf = ttk.Frame(hdr, style="H.TFrame"); bf.pack(fill="x", padx=24, pady=(0, 14))
        self._lbl_bval = ttk.Label(bf, text="--", style="Bal.TLabel")
        self._lbl_bval.pack(side="left")
        det = ttk.Frame(bf, style="H.TFrame"); det.pack(side="left", padx=(24, 0))
        self._lbl_avail  = ttk.Label(det, text="", style="H.TLabel");  self._lbl_avail.pack(anchor="w")
        self._lbl_grant  = ttk.Label(det, text="", style="Sm2.TLabel"); self._lbl_grant.pack(anchor="w")
        self._lbl_topup  = ttk.Label(det, text="", style="Sm2.TLabel"); self._lbl_topup.pack(anchor="w")

        tk.Frame(hdr, height=1, bg=C["border"]).pack(fill="x")

        # Tabs
        self._nb = ttk.Notebook(self.root)
        self._nb.pack(fill="both", expand=True, padx=12, pady=12)
        self._build_tab_overview()
        self._build_tab_settings()
        self._build_tab_history()

    def _build_tab_overview(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text=f"  {t('tab_overview')}  ")

        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True, padx=4, pady=4)

        self._ov_frame = ttk.Frame(sf.content, style="C.TFrame", padding=20)
        self._ov_frame.pack(fill="both", expand=True, padx=4, pady=4)

        ttk.Label(self._ov_frame, text=t("balance_info"), style="Sm.TLabel").pack(anchor="w")
        self._ov_bignum = ttk.Label(self._ov_frame, text="--", style="Mono.TLabel",
                                     font=("Consolas", 40, "bold"))
        self._ov_bignum.pack(anchor="w", pady=(4, 12))

        info_f = ttk.Frame(self._ov_frame, style="C.TFrame")
        info_f.pack(fill="x")
        self._ov_status_l = ttk.Label(info_f, text="", style="C.TLabel"); self._ov_status_l.pack(anchor="w", pady=2)
        self._ov_grant_l  = ttk.Label(info_f, text="", style="C.TLabel"); self._ov_grant_l.pack(anchor="w", pady=2)
        self._ov_topup_l  = ttk.Label(info_f, text="", style="C.TLabel"); self._ov_topup_l.pack(anchor="w", pady=2)

        # Pricing reference
        pf = ttk.Frame(self._ov_frame, style="C.TFrame", padding=16)
        pf.pack(fill="x", pady=(16, 0))
        self._pricing_title_lbl = ttk.Label(pf, text=t("pricing_title"), style="C.TLabel", font=F["sec"])
        self._pricing_title_lbl.pack(anchor="w", pady=(0, 6))
        self._pricing_text = tk.Label(pf, text=t("pricing_text"), font=F["mono"],
                                      bg=C["bg2"], fg=C["text2"], justify="left")
        self._pricing_text.pack(fill="x")

    def _build_tab_settings(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text=f"  {t('tab_settings')}  ")

        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True, padx=4, pady=4)

        content = sf.content

        pad = {"padx": 16, "pady": 8}

        # API Key
        kf = ttk.Frame(content, style="C.TFrame", padding=16)
        kf.pack(fill="x", **pad)
        self._sec_key = ttk.Label(kf, text=t("api_key"), style="C.TLabel", font=F["sec"])
        self._sec_key.pack(anchor="w")
        self._key_hint_lbl = ttk.Label(kf, text=t("api_key_hint"), style="Sm.TLabel")
        self._key_hint_lbl.pack(anchor="w", pady=(2, 8))
        ef = ttk.Frame(kf, style="C.TFrame"); ef.pack(fill="x")
        # Use entry with show="•" for masking — the StringVar holds the real value
        self._key_var = tk.StringVar(value=self._stored_key)
        self._key_entry = tk.Entry(ef, textvariable=self._key_var, show="•", font=F["mono"],
            bg=C["bg3"], fg=C["text"], insertbackground=C["text"], relief="flat", width=50)
        self._key_entry.pack(side="left", fill="x", expand=True, ipady=5)
        ttk.Button(ef, text="👁", width=3, command=self._toggle_key_vis).pack(side="left", padx=4)
        self._btn_save_key = ttk.Button(ef, text=t("save_key"), style="Acc.TButton", command=self._save_key)
        self._btn_save_key.pack(side="left", padx=4)

        # Refresh interval
        rf = ttk.Frame(content, style="C.TFrame", padding=16)
        rf.pack(fill="x", **pad)
        self._sec_int = ttk.Label(rf, text=t("refresh_int"), style="C.TLabel", font=F["sec"])
        self._sec_int.pack(anchor="w")
        self._refresh_hint_lbl = ttk.Label(rf, text=t("refresh_hint"), style="Sm.TLabel")
        self._refresh_hint_lbl.pack(anchor="w", pady=(2, 8))
        intf = ttk.Frame(rf, style="C.TFrame"); intf.pack(fill="x")
        self._int_var = tk.StringVar(value=str(self.config.refresh_interval))
        ttk.Combobox(intf, textvariable=self._int_var, state="readonly",
            values=["15","30","60","120","300","600","1800","3600"], width=8).pack(side="left")
        self._int_var.trace_add("write", lambda *_: self._save_interval())

        # Taskbar widget
        if HAS_TW:
            twf = ttk.Frame(content, style="C.TFrame", padding=16)
            twf.pack(fill="x", **pad)
            self._sec_tw = ttk.Label(twf, text=t("taskbar_wid"), style="C.TLabel", font=F["sec"])
            self._sec_tw.pack(anchor="w")
            self._taskbar_hint_lbl = ttk.Label(twf, text=t("taskbar_hint"), style="Sm.TLabel")
            self._taskbar_hint_lbl.pack(anchor="w", pady=(2, 8))
            # Enable / position row
            twr = ttk.Frame(twf, style="C.TFrame"); twr.pack(fill="x")
            self._tw_en = tk.BooleanVar(value=self.config.show_taskbar_widget)
            self._tw_chk = tk.Checkbutton(twr, text=t("enable"), variable=self._tw_en,
                bg=C["bg2"], fg=C["text"], selectcolor=C["bg3"],
                activebackground=C["bg2"], activeforeground=C["text"],
                command=self._toggle_tw)
            self._tw_chk.pack(side="left")
            ttk.Label(twr, text=f"  {t('position')}:", style="C.TLabel").pack(side="left", padx=(16, 4))
            self._tw_pos = tk.StringVar(value=self.config.taskbar_widget_position)
            ttk.Combobox(twr, textvariable=self._tw_pos, state="readonly",
                values=["right", "left"], width=8).pack(side="left")
            self._tw_pos.trace_add("write", lambda *_: self._toggle_tw())
            # Balance color pickers
            clr_f = ttk.Frame(twf, style="C.TFrame")
            clr_f.pack(fill="x", pady=(10, 0))
            self._tw_colors_label = ttk.Label(clr_f, text=t("balance_colors"), style="C.TLabel", font=F["small"])
            self._tw_colors_label.pack(side="left")
            self._tw_colors = {}      # key → swatch widget
            self._tw_color_tips = {}   # key → tip label widget
            th = self.config.tw_threshold_high
            tl = self.config.tw_threshold_low
            for key, cfg_attr, tip in [
                ("high", "tw_color_high", f"> {th:.0f}"),
                ("mid",  "tw_color_mid",  f"{tl:.0f} ~ {th:.0f}"),
                ("low",  "tw_color_low",  f"≤ {tl:.0f}"),
            ]:
                hex_val = getattr(self.config, cfg_attr, "")
                frm = ttk.Frame(clr_f, style="C.TFrame")
                frm.pack(side="left", padx=(8, 0))
                sw = tk.Label(frm, text="  ", bg=hex_val, relief="ridge",
                              bd=1, width=3, font=("", 1))
                sw.pack(side="left", padx=(0, 2))
                sw.bind("<Button-1>", lambda e, a=cfg_attr, s=sw: self._pick_color(a, s))
                tip_lbl = ttk.Label(frm, text=tip, style="Sm.TLabel")
                tip_lbl.pack(side="left")
                self._tw_colors[key] = sw
                self._tw_color_tips[key] = tip_lbl
            # Threshold entry fields
            thr_f = ttk.Frame(twf, style="C.TFrame")
            thr_f.pack(fill="x", pady=(8, 0))
            self._tw_thr_label = ttk.Label(thr_f, text=t("thresholds"), style="C.TLabel", font=F["small"])
            self._tw_thr_label.pack(side="left")
            self._tw_thr_high_var = tk.StringVar(value=str(self.config.tw_threshold_high))
            self._tw_thr_low_var  = tk.StringVar(value=str(self.config.tw_threshold_low))
            for lbl, var in [("  High:", self._tw_thr_high_var), ("  Low:", self._tw_thr_low_var)]:
                ttk.Label(thr_f, text=lbl, style="Sm.TLabel").pack(side="left")
                e = tk.Entry(thr_f, textvariable=var, font=F["mono"],
                             bg=C["bg3"], fg=C["text"], insertbackground=C["text"],
                             relief="flat", width=6, justify="center")
                e.pack(side="left", padx=(2, 0))
                e.bind("<FocusOut>", lambda _: self._save_thresholds())
                e.bind("<Return>", lambda _: self._save_thresholds())

        # Language
        lf = ttk.Frame(content, style="C.TFrame", padding=16)
        lf.pack(fill="x", **pad)
        self._sec_lang = ttk.Label(lf, text=t("language"), style="C.TLabel", font=F["sec"])
        self._sec_lang.pack(anchor="w")
        langf = ttk.Frame(lf, style="C.TFrame"); langf.pack(fill="x", pady=(8, 0))
        self._lang_var = tk.StringVar(value=self.config.language)
        ttk.Combobox(langf, textvariable=self._lang_var, state="readonly",
            values=["zh", "en"], width=8).pack(side="left")
        self._lang_var.trace_add("write", lambda *_: self._switch_lang())

        # Auto-start
        ast = ttk.Frame(content, style="C.TFrame", padding=16)
        ast.pack(fill="x", **pad)
        self._sec_auto_start = ttk.Label(ast, text=t("auto_start"), style="C.TLabel", font=F["sec"])
        self._sec_auto_start.pack(anchor="w")
        self._auto_start_var = tk.BooleanVar(value=self.config.auto_start)
        self._auto_start_chk = tk.Checkbutton(ast, text=t("auto_start"), variable=self._auto_start_var,
            bg=C["bg2"], fg=C["text"], selectcolor=C["bg3"],
            activebackground=C["bg2"], activeforeground=C["text"],
            command=self._toggle_auto_start)
        self._auto_start_chk.pack(anchor="w", pady=(6, 0))

        # About
        af = ttk.Frame(content, style="C.TFrame", padding=16)
        af.pack(fill="x", **pad)
        self._sec_about = ttk.Label(af, text=t("about"), style="C.TLabel", font=F["sec"])
        self._sec_about.pack(anchor="w")
        self._about_lbl = tk.Label(af, text=t("about_text"), font=F["body"],
            bg=C["bg2"], fg=C["text2"], justify="left", anchor="w", wraplength=600)
        self._about_lbl.pack(fill="x", pady=(6, 0))

    def _build_tab_history(self):
        tab = ttk.Frame(self._nb)
        self._nb.add(tab, text=f"  {t('tab_history')}  ")

        sf = ScrollableFrame(tab)
        sf.pack(fill="both", expand=True, padx=4, pady=4)

        # Range selector bar
        range_f = ttk.Frame(sf.content, style="C.TFrame")
        range_f.pack(fill="x", padx=8, pady=(8, 0))
        self._range_btns = {}
        self._range_active = tk.StringVar(value="day")
        for key in ["day", "week", "month", "quarter", "year"]:
            btn = tk.Button(range_f, text=t(f"range_{key}"), font=F["small"],
                            bg=C["btn"], fg=C["text"], relief="flat",
                            activebackground=C["btn_h"], activeforeground=C["text"],
                            command=lambda k=key: self._on_range_change(k))
            btn.pack(side="left", padx=2)
            self._range_btns[key] = btn
        self._update_range_highlight()

        # Chart area
        chart_f = ttk.Frame(sf.content, style="C.TFrame")
        chart_f.pack(fill="both", expand=True, padx=8, pady=8)
        self._chart = BalanceChart(chart_f, height=300)
        self._chart.pack(fill="both", expand=True)

        # Stats bar
        self._stats_f = ttk.Frame(sf.content, style="C.TFrame")
        self._stats_f.pack(fill="x", padx=16, pady=(0, 8))
        self._lbl_history_start = ttk.Label(self._stats_f, text="", style="Sm.TLabel")
        self._lbl_history_start.pack(side="left", padx=(0, 16))
        self._lbl_history_current = ttk.Label(self._stats_f, text="", style="Sm.TLabel")
        self._lbl_history_current.pack(side="left", padx=(0, 16))
        self._lbl_history_change = ttk.Label(self._stats_f, text="", style="Sm.TLabel")
        self._lbl_history_change.pack(side="left")

        # Load initial data
        self._refresh_chart()

    def _on_range_change(self, key: str):
        self._range_active.set(key)
        self._update_range_highlight()
        self._refresh_chart()

    def _update_range_highlight(self):
        active = self._range_active.get()
        for key, btn in self._range_btns.items():
            if key == active:
                btn.configure(bg=C["accent"], fg=C["bg"])
            else:
                btn.configure(bg=C["btn"], fg=C["text"])

    # ── Language switch ───────────────────────────────────────────────────────

    def _switch_lang(self):
        lang = self._lang_var.get()
        AppGlobals.lang = lang
        self.config.language = lang
        save_config(self.config)
        # Rebuild all text labels
        self._lbl_title.configure(text=t("title"))
        self._btn_refresh.configure(text=t("refresh"))
        self._nb.tab(0, text=f"  {t('tab_overview')}  ")
        self._nb.tab(1, text=f"  {t('tab_settings')}  ")
        # Settings tab
        self._sec_key.configure(text=t("api_key"))
        self._key_hint_lbl.configure(text=t("api_key_hint"))
        self._btn_save_key.configure(text=t("save_key"))
        self._sec_int.configure(text=t("refresh_int"))
        self._refresh_hint_lbl.configure(text=t("refresh_hint"))
        if HAS_TW:
            self._sec_tw.configure(text=t("taskbar_wid"))
            self._taskbar_hint_lbl.configure(text=t("taskbar_hint"))
            self._tw_chk.configure(text=t("enable"))
            self._tw_colors_label.configure(text=t("balance_colors"))
            self._tw_thr_label.configure(text=t("thresholds"))
        self._sec_lang.configure(text=t("language"))
        self._sec_auto_start.configure(text=t("auto_start"))
        self._auto_start_chk.configure(text=t("auto_start"))
        self._sec_about.configure(text=t("about"))
        self._about_lbl.configure(text=t("about_text"))
        # Overview tab
        self._pricing_title_lbl.configure(text=t("pricing_title"))
        self._pricing_text.configure(text=t("pricing_text"))
        # Update taskbar widget label
        if self._tw and self._tw.is_alive():
            self._tw.update_label(t("balance"))
        # Update threshold tip labels
        self._update_threshold_labels()
        # History tab
        self._nb.tab(2, text=f"  {t('tab_history')}  ")
        for key in ["day", "week", "month", "quarter", "year"]:
            if key in self._range_btns:
                self._range_btns[key].configure(text=t(f"range_{key}"))
        if hasattr(self, "_lbl_history_start"):
            self._refresh_chart()
        # Update balance display
        if self._last_data:
            self._display_balance(self._last_data)

    # ── Taskbar widget lifecycle ──────────────────────────────────────────────

    def _init_taskbar(self):
        if not HAS_TW or not self.config.show_taskbar_widget:
            return
        if not self.config.api_key:
            return  # don't start without key
        self._start_tw()

    def _start_tw(self):
        """Create and start a fresh taskbar widget (non-blocking).

        Any existing widget is cleaned up asynchronously so the main
        UI thread is never blocked.
        """
        old = self._tw
        self._tw = TaskbarWidget(
            api_key=self.config.api_key,
            label=t("balance"),         # i18n: "余额" or "Balance"
            refresh_seconds=self.config.refresh_interval,
            position=self.config.taskbar_widget_position,
            color_high=rgb_to_bgr(self.config.tw_color_high),
            color_mid=rgb_to_bgr(self.config.tw_color_mid),
            color_low=rgb_to_bgr(self.config.tw_color_low),
            color_label=rgb_to_bgr(self.config.tw_color_label),
            threshold_high=self.config.tw_threshold_high,
            threshold_low=self.config.tw_threshold_low,
        )
        self._tw.start()
        # Clean up old widget in background daemon thread
        if old:
            threading.Thread(target=old.stop_and_wait, daemon=True).start()

    def _stop_tw(self):
        """Stop the taskbar widget without blocking the main thread."""
        if self._tw:
            old = self._tw
            self._tw = None
            threading.Thread(target=old.stop_and_wait, daemon=True).start()

    def _toggle_tw(self):
        """Called when taskbar widget toggle or position changes."""
        enabled = self._tw_en.get()
        pos = self._tw_pos.get()
        self.config.show_taskbar_widget = enabled
        self.config.taskbar_widget_position = pos
        save_config(self.config)

        if enabled:
            if not self.config.api_key:
                messagebox.showwarning("DeepSeek Monitor", t("no_key"))
                self._tw_en.set(False)
                self.config.show_taskbar_widget = False
                save_config(self.config)
                return
            if self._tw and self._tw.is_alive():
                self._tw.update_position(self.config.taskbar_widget_position)
            else:
                self._start_tw()
        else:
            self._stop_tw()

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _init_tray(self):
        if sys.platform != "win32": return
        try:
            from src.tray import TrayIcon
        except Exception:
            logger.warning("Failed to import TrayIcon:\n%s", traceback.format_exc())
            return
        ico = BASE_PATH / "assets" / "favicon.ico"
        if not ico.exists():
            ico = DATA_DIR / "icon.png"
            if not ico.exists() and HAS_PIL:
                create_icon(ico, 64)
        self._tray = TrayIcon(
            tooltip="DeepSeek Monitor\nLoading...",
            icon_path=str(ico) if ico.exists() else None,
            on_left_double_click=lambda: self.root.after(0, self._raise),
            menu_items=[
                (t("btn_show"),    lambda: self.root.after(0, self._raise)),
                (t("btn_ref_now"), lambda: self.root.after(0, self._manual_refresh)),
                ("-", None),
                (t("auto_start"),
                 lambda: self.root.after(0, self._tray_toggle_auto_start),
                 lambda: self.config.auto_start),
                ("-", None),
                (t("btn_exit"),    lambda: self.root.after(0, self._quit)),
            ],
        )
        self._tray.start_bg()

    def _raise(self):
        self.root.deiconify(); self.root.state("normal"); self.root.lift(); self.root.focus_force()

    def _on_close(self):
        if self.config.minimize_to_tray and self._tray:
            self.root.withdraw()
            self._tray.show_balloon("DeepSeek Monitor", t("tray_msg"))
        else:
            self._quit()

    def _quit(self):
        if self._timer:
            try: self.root.after_cancel(self._timer)
            except: pass
        if self._tray:
            try: self._tray.stop()
            except: pass
        self._stop_tw()
        try:
            self.config.win_x = self.root.winfo_x()
            self.config.win_y = self.root.winfo_y()
            save_config(self.config)
        except Exception:
            logger.debug("Could not save window position", exc_info=True)
        self.root.destroy()

    # ── Data refresh ──────────────────────────────────────────────────────────

    def _schedule_midnight_compact(self):
        """Schedule a one-shot timer to compact history at 00:01.

        After firing, re-schedules itself for the next midnight.
        """
        from datetime import timedelta
        now = datetime.now()
        midnight = now.replace(hour=0, minute=1, second=0, microsecond=0)
        if now >= midnight:
            midnight += timedelta(days=1)
        delay_ms = int((midnight - now).total_seconds() * 1000)
        self.root.after(delay_ms, self._on_midnight_compact)

    def _on_midnight_compact(self):
        compact_all()
        self._refresh_chart()
        self._schedule_midnight_compact()  # re-arm for next night

    def _schedule(self):
        if self._timer:
            try: self.root.after_cancel(self._timer)
            except: pass
        self._timer = self.root.after(self.config.refresh_interval * 1000, self._tick)

    def _tick(self):
        self._refresh()
        self._timer = self.root.after(self.config.refresh_interval * 1000, self._tick)

    def _manual_refresh(self):
        self._refresh(); self._schedule()

    def _refresh(self):
        if self._busy: return
        if not self.config.api_key:
            self._login(); return
        if not self.client:
            self.client = DeepSeekClient(self.config.api_key)
        self._busy = True
        self._lbl_status.configure(text=t("fetching"))
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        data, err = None, None
        try: data = self.client.get_balance()
        except DeepSeekAPIError as e:
            err = str(e)
            logger.warning("Balance fetch failed: %s", e)
        except Exception as e:
            err = str(e)
            logger.exception("Unexpected error during balance fetch")
        self.root.after(0, lambda: self._on_done(data, err))

    def _on_done(self, data, err):
        self._busy = False
        now = datetime.now().strftime("%H:%M:%S")
        if err:
            self._lbl_status.configure(text=f"❌ {err}")
            if "401" in err: self.root.after(100, self._login)
            return
        if data:
            self._last_data = data
            self._display_balance(data)
            self._append_history(data)
            if self._tray:
                b = (data.get("balance_infos") or [{}])[0]
                sym = _currency_symbol(b.get("currency"))
                self._tray.update_tooltip(f"DeepSeek Monitor\n{sym}{float(b.get('total_balance', 0)):.2f}")
        self._lbl_status.configure(text=f"✅ {t('last_update')}: {now}")

    def _display_balance(self, data):
        """Update all balance displays using the shared formatter."""
        fb = _format_balance(data)
        if "error" in fb:
            self._lbl_bval.configure(text="N/A")
            return

        # Header bar
        self._lbl_bval.configure(text=fb["total"])
        self._lbl_avail.configure(text=fb["avail"])
        self._lbl_grant.configure(text=fb["granted"])
        self._lbl_topup.configure(text=fb["topup"])

        # Overview tab
        self._ov_bignum.configure(text=fb["total"])
        self._ov_status_l.configure(text=fb["avail"])
        self._ov_grant_l.configure(text=fb["granted"])
        self._ov_topup_l.configure(text=fb["topup"])

    # ── Balance History ───────────────────────────────────────────────────────

    _last_history_date: str = ""  # track day boundary for auto-compact

    def _append_history(self, data: dict):
        """Append a balance record to the day file, compact on day boundary."""
        fb = _format_balance(data)
        if "error" in fb:
            return
        record = {
            "ts": datetime.now().isoformat(sep="T", timespec="seconds"),
            "total": fb["total_raw"],
            "granted": float((data.get("balance_infos") or [{}])[0].get("granted_balance", 0)),
            "topup": float((data.get("balance_infos") or [{}])[0].get("topped_up_balance", 0)),
            "currency": (data.get("balance_infos") or [{}])[0].get("currency", "CNY"),
        }
        append_history_record(record)

        # Check day boundary — compact if we crossed midnight
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_history_date and self._last_history_date != today:
            compact_all()
        self._last_history_date = today

        self._refresh_chart()

    def _refresh_chart(self):
        """Reload history data from the appropriate layered file."""
        if not hasattr(self, "_chart"):
            return
        range_key = self._range_active.get()
        records = load_history(range_key)
        self._chart.set_data(records)
        # Update stats
        if records:
            start_total = records[0]["total"]
            end_total = records[-1]["total"]
            delta = end_total - start_total
            sym = _currency_symbol(records[0].get("currency", "CNY"))
            self._lbl_history_start.configure(
                text=f"{t('history_start')}: {sym}{start_total:.2f}")
            self._lbl_history_current.configure(
                text=f"{t('history_current')}: {sym}{end_total:.2f}")
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            color = C["green"] if delta > 0 else C["red"] if delta < 0 else C["text2"]
            self._lbl_history_change.configure(
                text=f"{t('history_change')}: {arrow} {sym}{abs(delta):.2f}",
                foreground=color)
        else:
            self._lbl_history_start.configure(text="")
            self._lbl_history_current.configure(text="")
            self._lbl_history_change.configure(text="")

    # ── Login ─────────────────────────────────────────────────────────────────

    def _login(self):
        dlg = tk.Toplevel(self.root)
        dlg.title(t("login_title")); dlg.configure(bg=C["bg"])
        dlg.geometry("460x240"); dlg.resizable(False, False)
        dlg.transient(self.root); dlg.grab_set()

        tk.Label(dlg, text=t("enter_key"), font=F["sec"], bg=C["bg"], fg=C["accent"]).pack(pady=(24, 10))
        ev = tk.StringVar()
        e = tk.Entry(dlg, textvariable=ev, show="•", font=F["mono"],
            bg=C["bg3"], fg=C["text"], insertbackground=C["text"], relief="flat", width=44)
        e.pack(pady=12, ipady=6); e.focus_set()
        res = {"k": None}
        def ok(): res["k"] = ev.get().strip(); dlg.destroy() if res["k"] else messagebox.showwarning("", t("key_empty"), parent=dlg)
        bf = tk.Frame(dlg, bg=C["bg"]); bf.pack(pady=(0, 12))
        ttk.Button(bf, text=t("login"), style="Acc.TButton", command=ok).pack(side="left", padx=6)
        ttk.Button(bf, text=t("cancel"), command=dlg.destroy).pack(side="left", padx=6)
        e.bind("<Return>", lambda _: ok())
        dlg.protocol("WM_DELETE_WINDOW", dlg.destroy); dlg.wait_window()

        if res["k"]:
            self.config.api_key = res["k"]
            self._stored_key = res["k"]
            # Update the settings entry to show the new key (it's still masked)
            self._key_var.set(res["k"])
            save_config(self.config)
            self.client = DeepSeekClient(res["k"])
            messagebox.showinfo("", t("key_saved"))
            # Start taskbar widget now that we have a key
            if self.config.show_taskbar_widget and HAS_TW:
                if self._tw and self._tw.is_alive():
                    self._tw.update_client(res["k"])
                else:
                    self._start_tw()
            self._refresh(); self._schedule()
        elif not self.config.api_key:
            self._lbl_status.configure(text=t("no_key"))

    # ── Settings helpers ──────────────────────────────────────────────────────

    def _toggle_auto_start(self):
        """Enable or disable auto-start with Windows."""
        enabled = self._auto_start_var.get()
        self.config.auto_start = enabled
        save_config(self.config)
        self._set_auto_start_registry(enabled)

    def _tray_toggle_auto_start(self):
        """Toggle auto-start from tray menu — keep checkbox in sync."""
        self.config.auto_start = not self.config.auto_start
        save_config(self.config)
        self._set_auto_start_registry(self.config.auto_start)
        self._auto_start_var.set(self.config.auto_start)

    def _set_auto_start_registry(self, enabled: bool):
        """Write or remove the registry entry for Windows auto-start."""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as key:
                if enabled:
                    exe = sys.executable if getattr(sys, "frozen", False) else sys.executable
                    winreg.SetValueEx(key, "DeepSeekMonitor", 0, winreg.REG_SZ, exe)
                    logger.info("Auto-start enabled: %s", exe)
                else:
                    try:
                        winreg.DeleteValue(key, "DeepSeekMonitor")
                        logger.info("Auto-start disabled")
                    except FileNotFoundError:
                        pass
        except Exception:
            logger.exception("Failed to update auto-start registry")

    def _pick_color(self, cfg_attr: str, swatch: tk.Label):
        """Open system color picker and apply the chosen color."""
        current = getattr(self.config, cfg_attr, "#808080")
        result = colorchooser.askcolor(color=current, parent=self.root,
                                       title="Pick balance color")
        if not result or not result[1]:
            return  # user cancelled
        hex_color = result[1]
        setattr(self.config, cfg_attr, hex_color)
        save_config(self.config)
        swatch.configure(bg=hex_color)
        # In-place update — no restart needed
        if self._tw and self._tw.is_alive():
            bgr = rgb_to_bgr(hex_color)
            kwargs = {}
            if cfg_attr == "tw_color_high":
                kwargs["color_high"] = bgr
            elif cfg_attr == "tw_color_mid":
                kwargs["color_mid"] = bgr
            elif cfg_attr == "tw_color_low":
                kwargs["color_low"] = bgr
            elif cfg_attr == "tw_color_label":
                kwargs["color_label"] = bgr
            self._tw.update_colors(**kwargs)

    def _save_thresholds(self):
        """Read threshold values from UI and save to config."""
        try:
            th = float(self._tw_thr_high_var.get())
            tl = float(self._tw_thr_low_var.get())
            if tl >= th:
                return  # invalid range, ignore
            self.config.tw_threshold_high = th
            self.config.tw_threshold_low  = tl
            save_config(self.config)
            self._update_threshold_labels()
            # In-place update — no restart needed
            if self._tw and self._tw.is_alive():
                self._tw.update_thresholds(threshold_high=th, threshold_low=tl)
        except ValueError:
            pass

    def _update_threshold_labels(self):
        """Refresh the threshold tip labels next to the colour swatches."""
        if not hasattr(self, "_tw_color_tips"):
            return
        th = self.config.tw_threshold_high
        tl = self.config.tw_threshold_low
        tips = {
            "high": f"> {th:.0f}",
            "mid":  f"{tl:.0f} ~ {th:.0f}",
            "low":  f"≤ {tl:.0f}",
        }
        for key, lbl in self._tw_color_tips.items():
            lbl.configure(text=tips[key])

    def _toggle_key_vis(self):
        cur = self._key_entry.cget("show")
        self._key_entry.configure(show="" if cur == "•" else "•")

    def _save_key(self):
        raw = self._key_var.get().strip()
        if not raw: messagebox.showwarning("", t("key_empty")); return
        self.config.api_key = raw
        self._stored_key = raw
        save_config(self.config)
        self.client = DeepSeekClient(raw)
        messagebox.showinfo("", t("key_saved"))
        if self.config.show_taskbar_widget and HAS_TW:
            if self._tw and self._tw.is_alive():
                self._tw.update_client(raw)
            else:
                self._start_tw()
        self._refresh()

    def _save_interval(self):
        try:
            v = int(self._int_var.get())
            self.config.refresh_interval = v; save_config(self.config)
            self._schedule()
            # In-place update — no restart needed
            if self._tw and self._tw.is_alive():
                self._tw.update_interval(v)
        except ValueError:
            pass

    # ── Run ───────────────────────────────────────────────────────────────────

    @classmethod
    def run(cls):
        root = tk.Tk()
        config = load_config()
        AppGlobals.lang = config.language
        cls(root, config)
        root.mainloop()
