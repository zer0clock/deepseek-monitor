"""
DeepSeek Monitor — PyQt5 dark glassmorphism UI.

Tabs: Spending Curve | Overview | Settings
"""

import logging
import sys
import threading
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget,
                              QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QLineEdit, QComboBox, QCheckBox, QFrame,
                              QMessageBox, QColorDialog, QDialog, QDialogButtonBox,
                              QSizePolicy, QSpacerItem, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QEvent, QObject, QMetaObject, Q_ARG, pyqtSlot
from PyQt5.QtGui import QFont, QColor, QIcon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if getattr(sys, "frozen", False):
    BASE_PATH = Path(sys._MEIPASS)
else:
    BASE_PATH = Path(__file__).resolve().parent.parent

from src.config import (Config, load_config, save_config, DATA_DIR,
                         load_history, append_history_record, compact_all,
                         rgb_to_bgr)
from src.api import DeepSeekClient, DeepSeekAPIError
from src.theme import C, F, build_stylesheet, set_theme_mode, get_theme_mode, is_light
from src.widgets import GlassCard, StatCard, CollapsibleSection, RangeSelector
from src.charts import BalanceChart

logger = logging.getLogger(__name__)

HAS_TW = sys.platform == "win32"
HAS_PIL = False
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    pass

# ══════════════════════════════════════════════════════════════════════════════
#  I18N
# ══════════════════════════════════════════════════════════════════════════════

T = {
    "en": {
        "title":              "💰 DeepSeek Monitor",
        "balance":            "Balance",
        "status":             "Status",
        "available":          "✅ Available",
        "insufficient":       "❌ Insufficient",
        "granted":            "Granted",
        "topup":              "Top-up",
        "refresh":            "🔄 Refresh",
        "last_update":        "Last updated",
        "fetching":           "⏳ Fetching...",
        "tab_spending":       "📊 Spending",
        "tab_overview":       "📊 Overview",
        "tab_settings":       "⚙ Settings",
        "api_key":            "🔑 API Key",
        "api_key_hint":       "Stored locally, never shared.",
        "save_key":           "Save Key",
        "refresh_int":        "⏱ Refresh Interval",
        "refresh_hint":       "How often to poll the balance API",
        "taskbar_wid":        "📌 Taskbar Widget",
        "taskbar_hint":       "Show balance directly on Windows taskbar",
        "balance_colors":     "Balance colors:",
        "thresholds":         "Thresholds:",
        "enable":             "Enable",
        "position":           "Position",
        "right":              "Right",
        "left":               "Left",
        "language":           "🌐 Language",
        "about":              "ℹ About",
        "about_text":         "DeepSeek Monitor v3.0\n"
                              "Lightweight Windows tool for monitoring DeepSeek API balance.\n\n"
                              "• Data: DeepSeek API (GET /user/balance)\n"
                              "• Set DEEPSEEK_API_KEY env var for auto-login",
        "login_title":        "Login — DeepSeek API Key",
        "enter_key":          "🔑 Enter your DeepSeek API Key",
        "login":              "Login",
        "cancel":             "Cancel",
        "key_empty":          "Please enter your API key.",
        "key_saved":          "API key saved. Refreshing...",
        "no_key":             "No API key configured",
        "balance_info":       "Total Balance",
        "no_data":            "No balance info",
        "pricing_title":      "💰 Model Pricing (CNY / 1M tokens)",
        "pricing_text":       "  Model              Input    Output   Cache Hit\n"
                              "  ────────────────────────────────────────────\n"
                              "  deepseek-v4-pro    ¥3.00    ¥6.00    ¥0.025\n"
                              "  deepseek-v4-flash  ¥1.00    ¥2.00    ¥0.02",
        "confirm_clr":         "Clear all local data?",
        "btn_exit":            "Exit",
        "btn_show":            "Show Window",
        "btn_ref_now":         "Refresh Now",
        "tray_msg":            "Running in background. Double-click tray icon to open.",
        "auto_start":          "Auto-start with Windows",
        "range_day":           "Day",
        "range_week":          "Week",
        "range_month":         "Month",
        "range_quarter":       "Qtr",
        "range_year":          "Year",
        "history_start":       "Start",
        "history_current":     "Current",
        "history_change":      "Change",
        "history_no_data":     "No data yet",
        "daily_spend":         "Today's Spend",
        "projected_days":      "Projected Days",
        "projected_days_fmt":  "≈ {} days remaining at current rate",
    },
    "zh": {
        "title":              "💰 DeepSeek 余额监控",
        "balance":            "余额",
        "status":             "状态",
        "available":          "✅ 可用",
        "insufficient":       "❌ 不足",
        "granted":            "赠送余额",
        "topup":              "充值余额",
        "refresh":            "🔄 刷新",
        "last_update":        "上次更新",
        "fetching":           "⏳ 获取中...",
        "tab_spending":       "📊 花费曲线",
        "tab_overview":       "📊 概览",
        "tab_settings":       "⚙ 设置",
        "api_key":            "🔑 API Key",
        "api_key_hint":       "仅保存在本地，不会发送给第三方。",
        "save_key":           "保存",
        "refresh_int":        "⏱ 刷新间隔",
        "refresh_hint":       "自动轮询余额 API 的频率",
        "taskbar_wid":        "📌 任务栏小组件",
        "taskbar_hint":       "在 Windows 任务栏上直接显示余额",
        "balance_colors":     "余额颜色：",
        "thresholds":         "阈值：",
        "enable":             "启用",
        "position":           "位置",
        "right":              "右侧",
        "left":               "左侧",
        "language":           "🌐 语言",
        "about":              "ℹ 关于",
        "about_text":         "DeepSeek 余额监控 v3.0\n"
                              "轻量级 Windows 余额查询工具。\n\n"
                              "• 数据来源：DeepSeek API (GET /user/balance)\n"
                              "• 设置环境变量 DEEPSEEK_API_KEY 自动登录",
        "login_title":        "登录 — DeepSeek API Key",
        "enter_key":          "🔑 请输入 DeepSeek API Key",
        "login":              "登录",
        "cancel":             "取消",
        "key_empty":          "请输入 API Key。",
        "key_saved":          "已保存，正在刷新...",
        "no_key":             "未配置 API Key",
        "balance_info":       "总余额",
        "no_data":            "暂无余额信息",
        "pricing_title":      "💰 模型定价 (CNY / 1M tokens)",
        "pricing_text":       "  Model              Input    Output   Cache Hit\n"
                              "  ────────────────────────────────────────────\n"
                              "  deepseek-v4-pro    ¥3.00    ¥6.00    ¥0.025\n"
                              "  deepseek-v4-flash  ¥1.00    ¥2.00    ¥0.02",
        "confirm_clr":         "确定清除所有本地数据？",
        "btn_exit":            "退出",
        "btn_show":            "显示窗口",
        "btn_ref_now":         "立即刷新",
        "tray_msg":            "已最小化到后台，双击托盘图标打开。",
        "auto_start":          "开机自启",
        "range_day":           "日",
        "range_week":          "周",
        "range_month":         "月",
        "range_quarter":       "季度",
        "range_year":          "年",
        "history_start":       "起始",
        "history_current":     "当前",
        "history_change":      "变化",
        "history_no_data":     "暂无数据",
        "daily_spend":         "今日花费",
        "projected_days":      "预计可用天数",
        "projected_days_fmt":  "按近 7 天日均花费计算，剩余可用约 {} 天",
    },
}


class AppGlobals:
    lang: str = "zh"


def t(key: str) -> str:
    lang = AppGlobals.lang
    return T.get(lang, T["en"]).get(key, key)


def _currency_symbol(currency: Optional[str]) -> str:
    if currency == "USD": return "$"
    if currency == "CNY": return "¥"
    return currency or "¥"


def _format_balance(data: Dict) -> Dict[str, str]:
    infos = data.get("balance_infos", [])
    if not infos:
        return {"error": t("no_data")}
    b = infos[0]
    total = float(b.get("total_balance", 0))
    granted = float(b.get("granted_balance", 0))
    topped = float(b.get("topped_up_balance", 0))
    sym = _currency_symbol(b.get("currency"))
    avail = data.get("is_available", False)
    return {
        "total":    f"{sym}{total:.2f}",
        "avail":    f"{t('status')}: {t('available') if avail else t('insufficient')}",
        "granted":  f"{t('granted')}: {sym}{granted:.2f}",
        "topup":    f"{t('topup')}:  {sym}{topped:.2f}",
        "is_avail": avail,
        "total_raw": total,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

class WheelBlocker(QObject):
    """Event filter that blocks mouse wheel events on combo boxes."""
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True  # swallow wheel event
        return super().eventFilter(obj, event)


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

class DeepSeekMonitorApp(QMainWindow):

    def __init__(self, config: Config):
        super().__init__()
        super().__init__()
        self.config = config
        self.client: Optional[DeepSeekClient] = None
        self._tray = None
        self._tw = None
        self._last_data: Optional[Dict] = None
        self._stored_key: str = config.api_key
        self._last_history_date: str = ""
        AppGlobals.lang = config.language

        self.setWindowTitle("DeepSeek Monitor")
        self.setMinimumSize(860, 560)
        self.resize(960, 660)
        if config.win_x is not None:
            self.move(config.win_x, config.win_y)

        # Apply stylesheet
        set_theme_mode(self.config.theme_mode)
        self.setStyleSheet(build_stylesheet())

        # Icon
        ico = BASE_PATH / "assets" / "favicon.ico"
        if ico.exists():
            self.setWindowIcon(QIcon(str(ico)))

        self._build_ui()

        # Compact history + midnight timer
        compact_all()
        self._last_history_date = datetime.now().strftime("%Y-%m-%d")
        self._schedule_midnight_compact()

        # Auto-start registry
        if self.config.auto_start:
            self._set_auto_start_registry(True)

        # Init tray & taskbar
        self._init_tray()
        self._init_taskbar()

        if self.config.api_key:
            QTimer.singleShot(300, self._refresh)
            QTimer.singleShot(600, self._schedule)
        else:
            QTimer.singleShot(200, self._login)

    # ── UI Build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        root.addWidget(self._build_header())

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        root.addWidget(self._tabs, 1)

        self._build_tab_spending()
        self._build_tab_overview()
        self._build_tab_settings()
        self._refresh_chart()

    def _build_header(self):
        hdr = QFrame()
        hdr.setStyleSheet(f"background-color: {C['header']}; border-bottom: 2px solid {C['accent']};")
        layout = QVBoxLayout(hdr)
        layout.setContentsMargins(24, 14, 24, 12)

        # Row 1: title + refresh + status
        r1 = QHBoxLayout()
        self._lbl_title = QLabel(t("title"))
        self._lbl_title.setStyleSheet(f"font-weight: bold; font-size: 20pt; color: {C['text']}; border: none; background: transparent;")
        r1.addWidget(self._lbl_title)
        r1.addStretch()
        self._btn_refresh = QPushButton(t("refresh"))
        self._btn_refresh.clicked.connect(self._manual_refresh)
        r1.addWidget(self._btn_refresh)
        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
        r1.addWidget(self._lbl_status)
        layout.addLayout(r1)

        # Row 2: 4 stat cards
        r2 = QHBoxLayout()
        r2.setSpacing(12)
        self._card_balance = StatCard(t("balance"))
        self._card_status = StatCard(t("status"))
        self._card_granted = StatCard(t("granted"))
        self._card_topup = StatCard(t("topup"))
        for c in [self._card_balance, self._card_status, self._card_granted, self._card_topup]:
            r2.addWidget(c)
        layout.addLayout(r2)
        return hdr

    def _build_tab_spending(self):
        tab = QWidget()
        self._tabs.addTab(tab, f"  {t('tab_spending')}  ")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 8, 12, 8)

        range_items = [(k, t(f"range_{k}")) for k in ["day", "week", "month", "quarter", "year"]]
        self._range_sel = RangeSelector(range_items, active="day")
        layout.addWidget(self._range_sel)

        self._chart = BalanceChart()
        layout.addWidget(self._chart, 1)

        stats = QHBoxLayout()
        self._lbl_hist_start = QLabel("")
        self._lbl_hist_start.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        stats.addWidget(self._lbl_hist_start)
        self._lbl_hist_curr = QLabel("")
        self._lbl_hist_curr.setStyleSheet(f"color: {C['text2']}; font-size: 9pt;")
        stats.addWidget(self._lbl_hist_curr)
        self._lbl_hist_change = QLabel("")
        stats.addWidget(self._lbl_hist_change)
        stats.addStretch()
        layout.addLayout(stats)

        # Wire range buttons
        for btn in self._range_sel._buttons.values():
            btn.clicked.connect(lambda: self._on_range_change())

    def _build_tab_overview(self):
        tab = QWidget()
        self._tabs.addTab(tab, f"  {t('tab_overview')}  ")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {C['bg']}; }} QScrollArea > QWidget > QWidget {{ background-color: {C['bg']}; }}")
        out = QVBoxLayout(tab)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background-color: {C['bg']};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 2x2 stat cards
        grid1 = QHBoxLayout()
        grid1.setSpacing(12)
        self._ov_balance = StatCard(t("balance_info"))
        self._ov_spend = StatCard(t("daily_spend"))
        self._ov_granted = StatCard(t("granted"))
        self._ov_topup = StatCard(t("topup"))
        grid1.addWidget(self._ov_balance)
        grid1.addWidget(self._ov_spend)
        grid2 = QHBoxLayout()
        grid2.setSpacing(12)
        grid2.addWidget(self._ov_granted)
        grid2.addWidget(self._ov_topup)
        layout.addLayout(grid1)
        layout.addLayout(grid2)

        # Projected days card
        proj_card = GlassCard()
        self._lbl_projected = QLabel("")
        self._lbl_projected.setStyleSheet(f"color: {C['text']}; font-size: 10pt; border: none; background: transparent;")
        proj_card._layout.addWidget(self._lbl_projected)
        layout.addWidget(proj_card)

        # Pricing card
        price_card = GlassCard(t("pricing_title"))
        self._lbl_pricing = QLabel(t("pricing_text"))
        self._lbl_pricing.setStyleSheet(
            f"font-family: Consolas; font-size: 10pt; color: {C['text2']}; "
            f"border: none; background: transparent;")
        price_card._layout.addWidget(self._lbl_pricing)
        layout.addWidget(price_card)

        layout.addStretch()
        scroll.setWidget(content)

    def _build_tab_settings(self):
        tab = QWidget()
        self._tabs.addTab(tab, f"  {t('tab_settings')}  ")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {C['bg']}; }} QScrollArea > QWidget > QWidget {{ background-color: {C['bg']}; }}")
        out = QVBoxLayout(tab)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background-color: {C['bg']};")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(6)

        # --- API Key ---
        sec_key = CollapsibleSection(t("api_key"))
        self._sec_key = sec_key
        klay = sec_key.content_layout()
        hint = QLabel(t("api_key_hint"))
        hint.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
        klay.addWidget(hint)
        kr = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.Password)
        self._key_input.setText(self._stored_key)
        kr.addWidget(self._key_input, 1)
        btn_vis = QPushButton("👁")
        btn_vis.setFixedWidth(36)
        btn_vis.clicked.connect(self._toggle_key_vis)
        kr.addWidget(btn_vis)
        btn_save = QPushButton(t("save_key"))
        btn_save.setObjectName("accentBtn")
        btn_save.clicked.connect(self._save_key)
        kr.addWidget(btn_save)
        klay.addLayout(kr)
        layout.addWidget(sec_key)

        # --- Refresh Interval ---
        sec_int = CollapsibleSection(t("refresh_int"))
        self._sec_int = sec_int
        ilay = sec_int.content_layout()
        ihint = QLabel(t("refresh_hint"))
        ihint.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
        ilay.addWidget(ihint)
        val_list = ["15", "30", "60", "120", "300", "600", "1800", "3600"]
        self._cmb_interval = QComboBox()
        self._cmb_interval.installEventFilter(WheelBlocker(self._cmb_interval))
        self._cmb_interval.addItems(val_list)
        self._cmb_interval.setCurrentText(str(self.config.refresh_interval))
        self._cmb_interval.currentTextChanged.connect(self._save_interval)
        ilay.addWidget(self._cmb_interval)
        layout.addWidget(sec_int)

        # --- Taskbar Widget (collapsed by default) ---
        if HAS_TW:
            sec_tw = CollapsibleSection(t("taskbar_wid"), collapsed=True)
            self._sec_tw = sec_tw
            tlay = sec_tw.content_layout()
            thint = QLabel(t("taskbar_hint"))
            thint.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
            tlay.addWidget(thint)
            # Enable + position
            tr = QHBoxLayout()
            self._tw_en_cb = QCheckBox(t("enable"))
            self._tw_en_cb.setChecked(self.config.show_taskbar_widget)
            self._tw_en_cb.toggled.connect(self._toggle_tw)
            tr.addWidget(self._tw_en_cb)
            tr.addWidget(QLabel(t("position") + ":"))
            self._cmb_tw_pos = QComboBox()
            self._cmb_tw_pos.installEventFilter(WheelBlocker(self._cmb_tw_pos))
            self._cmb_tw_pos.addItems([t("right"), t("left")])
            self._cmb_tw_pos.setCurrentText(t(self.config.taskbar_widget_position))
            self._cmb_tw_pos.currentTextChanged.connect(self._toggle_tw)
            self._cmb_tw_pos.setFixedWidth(80)
            tr.addWidget(self._cmb_tw_pos)
            tr.addStretch()
            tlay.addLayout(tr)
            # Color swatches
            clr_f = QHBoxLayout()
            clr_f.addWidget(QLabel(t("balance_colors")))
            clr_lbl = clr_f.itemAt(clr_f.count() - 1).widget()
            clr_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
            self._tw_colors = {}
            self._tw_color_tips = {}
            th = self.config.tw_threshold_high
            tl = self.config.tw_threshold_low
            for key, cfg_attr, tip in [
                ("high", "tw_color_high", f"> {th:.0f}"),
                ("mid",  "tw_color_mid",  f"{tl:.0f} ~ {th:.0f}"),
                ("low",  "tw_color_low",  f"≤ {tl:.0f}"),
            ]:
                hex_val = getattr(self.config, cfg_attr, "")
                btn = QPushButton("")
                btn.setFixedSize(28, 20)
                btn.setStyleSheet(
                    f"background-color: {hex_val}; border: 1px solid {C['border']}; "
                    f"border-radius: 4px;")
                btn.clicked.connect(lambda _, a=cfg_attr, b=btn: self._pick_color(a, b))
                clr_f.addWidget(btn)
                self._tw_colors[key] = btn
                tip_lbl = QLabel(tip)
                tip_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
                clr_f.addWidget(tip_lbl)
                self._tw_color_tips[key] = tip_lbl
            clr_f.addStretch()
            tlay.addLayout(clr_f)
            # Thresholds
            thr_f = QHBoxLayout()
            thr_f.addWidget(QLabel(t("thresholds")))
            thr_lbl = thr_f.itemAt(thr_f.count() - 1).widget()
            thr_lbl.setStyleSheet(f"color: {C['text2']}; font-size: 9pt; border: none; background: transparent;")
            self._tw_thr_high = QLineEdit(str(self.config.tw_threshold_high))
            self._tw_thr_high.setFixedWidth(60)
            self._tw_thr_high.editingFinished.connect(self._save_thresholds)
            self._tw_thr_low = QLineEdit(str(self.config.tw_threshold_low))
            self._tw_thr_low.setFixedWidth(60)
            self._tw_thr_low.editingFinished.connect(self._save_thresholds)
            thr_f.addWidget(QLabel("High:"))
            thr_f.addWidget(self._tw_thr_high)
            thr_f.addWidget(QLabel("Low:"))
            thr_f.addWidget(self._tw_thr_low)
            thr_f.addStretch()
            tlay.addLayout(thr_f)
            layout.addWidget(sec_tw)

        # --- Theme ---
        sec_theme = CollapsibleSection("🎨 Theme", collapsed=True)
        tlay_th = sec_theme.content_layout()
        theme_f = QHBoxLayout()
        self._theme_btns = {}
        theme_items = [("light", "☀️ Light"), ("dark", "🌙 Dark"), ("system", "🔄 System")]
        for key, label in theme_items:
            btn = QPushButton(label)
            btn.setObjectName("rangeBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            if key == self.config.theme_mode:
                btn.setChecked(True)
                btn.setStyleSheet(f"background-color: {C['accent']}; color: white; border: none; border-radius: 4px; padding: 4px 12px;")
            btn.clicked.connect(lambda _, k=key: self._on_theme_change(k))
            self._theme_btns[key] = btn
            theme_f.addWidget(btn)
        theme_f.addStretch()
        tlay_th.addLayout(theme_f)
        layout.addWidget(sec_theme)

        # --- Language ---
        sec_lang = CollapsibleSection(t("language"), collapsed=True)
        self._sec_lang = sec_lang
        llay = sec_lang.content_layout()
        self._cmb_lang = QComboBox()
        self._cmb_lang.installEventFilter(WheelBlocker(self._cmb_lang))
        self._cmb_lang.addItems(["zh", "en"])
        self._cmb_lang.setCurrentText(self.config.language)
        self._cmb_lang.currentTextChanged.connect(self._switch_lang)
        llay.addWidget(self._cmb_lang)
        layout.addWidget(sec_lang)

        # --- Auto-start ---
        sec_as = CollapsibleSection(t("auto_start"), collapsed=True)
        self._sec_auto_start = sec_as
        alay = sec_as.content_layout()
        self._cb_auto_start = QCheckBox(t("auto_start"))
        self._cb_auto_start.setChecked(self.config.auto_start)
        self._cb_auto_start.toggled.connect(self._toggle_auto_start)
        alay.addWidget(self._cb_auto_start)
        layout.addWidget(sec_as)

        # --- About ---
        sec_about = CollapsibleSection(t("about"), collapsed=True)
        self._sec_about = sec_about
        alay2 = sec_about.content_layout()
        self._lbl_about = QLabel(t("about_text"))
        self._lbl_about.setStyleSheet(f"color: {C['text2']}; font-size: 10pt; border: none; background: transparent;")
        self._lbl_about.setWordWrap(True)
        alay2.addWidget(self._lbl_about)
        layout.addWidget(sec_about)

        layout.addStretch()
        scroll.setWidget(content)

    # ── Language ──────────────────────────────────────────────────────────────

    def _switch_lang(self):
        lang = self._cmb_lang.currentText()
        AppGlobals.lang = lang
        self.config.language = lang
        save_config(self.config)
        # Refresh all UI text
        self._lbl_title.setText(t("title"))
        self._btn_refresh.setText(t("refresh"))
        self._tabs.setTabText(0, f"  {t('tab_spending')}  ")
        self._tabs.setTabText(1, f"  {t('tab_overview')}  ")
        self._tabs.setTabText(2, f"  {t('tab_settings')}  ")
        for card, key in [(self._card_balance, "balance"), (self._card_status, "status"),
                          (self._card_granted, "granted"), (self._card_topup, "topup")]:
            card.set_label(t(key))
        # Overview
        self._ov_balance.set_label(t("balance_info"))
        self._ov_spend.set_label(t("daily_spend"))
        self._ov_granted.set_label(t("granted"))
        self._ov_topup.set_label(t("topup"))
        self._lbl_pricing.setText(t("pricing_text"))
        # Settings sections
        self._sec_key.set_title(t("api_key"))
        self._sec_int.set_title(t("refresh_int"))
        if HAS_TW:
            self._sec_tw.set_title(t("taskbar_wid"))
        self._sec_lang.set_title(t("language"))
        self._sec_auto_start.set_title(t("auto_start"))
        self._cb_auto_start.setText(t("auto_start"))
        self._sec_about.set_title(t("about"))
        self._lbl_about.setText(t("about_text"))
        # Spending tab
        for btn in self._range_sel._buttons.values():
            k = btn.property("range_key")
            if k:
                btn.setText(t(f"range_{k}"))
        self._update_threshold_labels()
        if self._tw and self._tw.is_alive():
            self._tw.update_label(t("balance"))
        if self._last_data:
            self._display_balance(self._last_data)
        self._refresh_chart()

    # ── Taskbar Widget ────────────────────────────────────────────────────────

    def _init_taskbar(self):
        if not HAS_TW or not self.config.show_taskbar_widget:
            return
        if not self.config.api_key:
            return
        self._start_tw()

    def _start_tw(self):
        from src.taskbar_widget import TaskbarWidget
        old = self._tw
        self._tw = TaskbarWidget(
            api_key=self.config.api_key,
            label=t("balance"),
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
        if old:
            threading.Thread(target=old.stop_and_wait, daemon=True).start()

    def _stop_tw(self):
        if self._tw:
            old = self._tw
            self._tw = None
            threading.Thread(target=old.stop_and_wait, daemon=True).start()

    def _toggle_tw(self):
        enabled = self._tw_en_cb.isChecked()
        pos_text = self._cmb_tw_pos.currentText()
        pos = "right" if pos_text in [t("right"), "Right"] else "left"
        self.config.show_taskbar_widget = enabled
        self.config.taskbar_widget_position = pos
        save_config(self.config)
        if enabled:
            if not self.config.api_key:
                QMessageBox.warning(self, "DeepSeek Monitor", t("no_key"))
                self._tw_en_cb.setChecked(False)
                return
            if self._tw and self._tw.is_alive():
                self._tw.update_position(self.config.taskbar_widget_position)
            else:
                self._start_tw()
        else:
            self._stop_tw()

    def _pick_color(self, cfg_attr: str, btn: QPushButton):
        current = getattr(self.config, cfg_attr, "#808080")
        color = QColorDialog.getColor(QColor(current), self, "Pick balance color")
        if not color.isValid():
            return
        hex_color = color.name()
        setattr(self.config, cfg_attr, hex_color)
        save_config(self.config)
        btn.setStyleSheet(
            f"background-color: {hex_color}; border: 1px solid {C['border']}; border-radius: 4px;")
        if self._tw and self._tw.is_alive():
            bgr = rgb_to_bgr(hex_color)
            kwargs = {}
            if cfg_attr == "tw_color_high": kwargs["color_high"] = bgr
            elif cfg_attr == "tw_color_mid": kwargs["color_mid"] = bgr
            elif cfg_attr == "tw_color_low": kwargs["color_low"] = bgr
            elif cfg_attr == "tw_color_label": kwargs["color_label"] = bgr
            self._tw.update_colors(**kwargs)

    def _save_thresholds(self):
        try:
            th = float(self._tw_thr_high.text())
            tl = float(self._tw_thr_low.text())
            if tl >= th: return
            self.config.tw_threshold_high = th
            self.config.tw_threshold_low = tl
            save_config(self.config)
            self._update_threshold_labels()
            if self._tw and self._tw.is_alive():
                self._tw.update_thresholds(threshold_high=th, threshold_low=tl)
        except ValueError:
            pass

    def _update_threshold_labels(self):
        if not hasattr(self, "_tw_color_tips") or not self._tw_color_tips:
            return
        th = self.config.tw_threshold_high
        tl = self.config.tw_threshold_low
        tips = {"high": f"> {th:.0f}", "mid": f"{tl:.0f} ~ {th:.0f}", "low": f"≤ {tl:.0f}"}
        for key, lbl in self._tw_color_tips.items():
            lbl.setText(tips[key])

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _init_tray(self):
        if sys.platform != "win32": return
        try:
            from src.tray import TrayIcon
        except Exception:
            logger.warning("Failed TrayIcon: %s", traceback.format_exc())
            return
        ico = BASE_PATH / "assets" / "favicon.ico"
        if not ico.exists():
            ico = DATA_DIR / "icon.png"
            if not ico.exists() and HAS_PIL:
                self._create_icon(ico, 64)
        self._tray = TrayIcon(
            tooltip="DeepSeek Monitor\nLoading...",
            icon_path=str(ico) if ico.exists() else None,
            on_left_double_click=lambda: self._raise(),
            menu_items=[
                (t("btn_show"),    lambda: self._raise()),
                (t("btn_ref_now"), lambda: self._manual_refresh()),
                ("-", None),
                (t("auto_start"),
                 lambda: self._tray_toggle_auto_start(),
                 lambda: self.config.auto_start),
                ("-", None),
                (t("btn_exit"),    lambda: self._quit()),
            ],
        )
        self._tray.start_bg()

    def _create_icon(self, path: Path, size: int = 64):
        if not HAS_PIL: return
        try:
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([2, 2, size - 2, size - 2], fill="#89b4fa", outline="#585b70", width=2)
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(path))
        except Exception:
            pass

    def _raise(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        if self.config.minimize_to_tray and self._tray:
            self.hide()
            self._tray.show_balloon("DeepSeek Monitor", t("tray_msg"))
            event.ignore()
        else:
            self._quit()

    def _quit(self):
        if self._tray:
            try: self._tray.stop()
            except: pass
        self._stop_tw()
        try:
            self.config.win_x = self.x()
            self.config.win_y = self.y()
            save_config(self.config)
        except Exception:
            pass
        QApplication.quit()

    # ── Data Refresh ─────────────────────────────────────────────────────────

    def _schedule(self):
        ms = self.config.refresh_interval * 1000
        QTimer.singleShot(ms, self._tick)

    def _tick(self):
        self._refresh()
        QTimer.singleShot(self.config.refresh_interval * 1000, self._tick)

    def _manual_refresh(self):
        self._refresh()
        self._schedule()

    def _refresh(self):
        if not self.config.api_key:
            self._login()
            return
        if not self.client:
            self.client = DeepSeekClient(self.config.api_key)
        self._lbl_status.setText(t("fetching"))
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        data, err = None, None
        try:
            data = self.client.get_balance()
        except DeepSeekAPIError as e:
            err = str(e)
        except Exception as e:
            err = str(e)
            logger.exception("Fetch failed")
        QMetaObject.invokeMethod(
            self, "_on_done", Qt.QueuedConnection,
            Q_ARG(object, data), Q_ARG(object, err))

    @pyqtSlot(object, object)
    def _on_done(self, data, err):
        now = datetime.now().strftime("%H:%M:%S")
        if err:
            self._lbl_status.setText(f"❌ {err}")
            if "401" in err:
                QTimer.singleShot(100, self._login)
            return
        if data:
            self._last_data = data
            self._display_balance(data)
            self._append_history(data)
            if self._tray:
                b = (data.get("balance_infos") or [{}])[0]
                sym = _currency_symbol(b.get("currency"))
                self._tray.update_tooltip(
                    f"DeepSeek Monitor\n{sym}{float(b.get('total_balance', 0)):.2f}")
        self._lbl_status.setText(f"✅ {t('last_update')}: {now}")

    def _display_balance(self, data):
        fb = _format_balance(data)
        if "error" in fb: return
        total = fb["total"]
        is_avail = fb.get("is_avail", False)
        avail_color = C["green"] if is_avail else C["red"]
        self._card_balance.set_value(total, C["accent"])
        self._card_status.set_value(t("available") if is_avail else t("insufficient"), avail_color)
        self._card_granted.set_value(fb["granted"].split(": ", 1)[-1])
        self._card_topup.set_value(fb["topup"].split(": ", 1)[-1])
        # Overview tab
        self._ov_balance.set_value(total, C["accent"])
        self._ov_granted.set_value(fb["granted"].split(": ", 1)[-1])
        self._ov_topup.set_value(fb["topup"].split(": ", 1)[-1])
        # Daily spend & projected days
        self._update_daily_stats()

    def _update_daily_stats(self):
        day_records = load_history("day")
        if day_records:
            start = day_records[0]["total"]
            end = day_records[-1]["total"]
            spend = start - end
            sym = _currency_symbol(day_records[0].get("currency", "CNY"))
            color = C["red"] if spend > 0 else C["green"] if spend < 0 else C["text2"]
            self._ov_spend.set_value(f"{'−' if spend >= 0 else '+'}{sym}{abs(spend):.2f}", color)
            # Projected days: last 7 days avg
            week_records = load_history("week")
            if len(week_records) >= 2:
                w_start = week_records[0]["total"]
                w_end = week_records[-1]["total"]
                days = max(1, len(week_records) / 24) if len(week_records) > 24 else 1
                daily_avg = (w_start - w_end) / max(days, 1)
                if daily_avg > 0:
                    proj = end / daily_avg
                    self._lbl_projected.setText(
                        t("projected_days_fmt").format(int(proj)))
                else:
                    self._lbl_projected.setText("")
            else:
                self._lbl_projected.setText("")

    # ── History ───────────────────────────────────────────────────────────────

    def _append_history(self, data):
        fb = _format_balance(data)
        if "error" in fb: return
        record = {
            "ts": datetime.now().isoformat(sep="T", timespec="seconds"),
            "total": fb["total_raw"],
            "granted": float((data.get("balance_infos") or [{}])[0].get("granted_balance", 0)),
            "topup": float((data.get("balance_infos") or [{}])[0].get("topped_up_balance", 0)),
            "currency": (data.get("balance_infos") or [{}])[0].get("currency", "CNY"),
        }
        append_history_record(record)
        today = datetime.now().strftime("%Y-%m-%d")
        if self._last_history_date and self._last_history_date != today:
            compact_all()
        self._last_history_date = today
        self._refresh_chart()

    def _on_range_change(self):
        self._refresh_chart()

    def _refresh_chart(self):
        if not hasattr(self, "_chart"): return
        key = self._range_sel.active
        records = load_history(key)
        self._chart.set_data(records)
        if records:
            start_total = records[0]["total"]
            end_total = records[-1]["total"]
            delta = end_total - start_total
            sym = _currency_symbol(records[0].get("currency", "CNY"))
            self._lbl_hist_start.setText(f"{t('history_start')}: {sym}{start_total:.2f}")
            self._lbl_hist_curr.setText(f"{t('history_current')}: {sym}{end_total:.2f}")
            arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
            color = C["green"] if delta > 0 else C["red"] if delta < 0 else C["text2"]
            self._lbl_hist_change.setText(
                f"{t('history_change')}: {arrow} {sym}{abs(delta):.2f}")
            self._lbl_hist_change.setStyleSheet(f"color: {color}; font-size: 9pt;")
        else:
            self._lbl_hist_start.setText("")
            self._lbl_hist_curr.setText("")
            self._lbl_hist_change.setText("")

    def _schedule_midnight_compact(self):
        now = datetime.now()
        midnight = now.replace(hour=0, minute=1, second=0, microsecond=0)
        if now >= midnight:
            midnight += timedelta(days=1)
        delay_ms = int((midnight - now).total_seconds() * 1000)
        QTimer.singleShot(delay_ms, self._on_midnight_compact)

    def _on_midnight_compact(self):
        compact_all()
        self._refresh_chart()
        self._schedule_midnight_compact()

    # ── Login ─────────────────────────────────────────────────────────────────

    def _login(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(t("login_title"))
        dlg.setFixedSize(460, 220)
        dlg.setStyleSheet(f"background-color: {C['bg']};")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(t("enter_key")))
        ev = QLineEdit()
        ev.setEchoMode(QLineEdit.Password)
        layout.addWidget(ev)
        ev.setFocus()

        btn_box = QDialogButtonBox()
        login_btn = QPushButton(t("login"))
        login_btn.setObjectName("accentBtn")
        cancel_btn = QPushButton(t("cancel"))
        btn_box.addButton(login_btn, QDialogButtonBox.AcceptRole)
        btn_box.addButton(cancel_btn, QDialogButtonBox.RejectRole)
        layout.addWidget(btn_box)

        login_btn.clicked.connect(lambda: dlg.accept() if ev.text().strip() else
                                  QMessageBox.warning(dlg, "", t("key_empty")))
        cancel_btn.clicked.connect(dlg.reject)

        if dlg.exec() == QDialog.Accepted:
            key = ev.text().strip()
            self.config.api_key = key
            self._stored_key = key
            self._key_input.setText(key)
            save_config(self.config)
            self.client = DeepSeekClient(key)
            QMessageBox.information(self, "", t("key_saved"))
            if self.config.show_taskbar_widget and HAS_TW:
                if self._tw and self._tw.is_alive():
                    self._tw.update_client(key)
                else:
                    self._start_tw()
            self._refresh()
            self._schedule()
        elif not self.config.api_key:
            self._lbl_status.setText(t("no_key"))

    # ── Settings Helpers ──────────────────────────────────────────────────────

    def _toggle_key_vis(self):
        if self._key_input.echoMode() == QLineEdit.Password:
            self._key_input.setEchoMode(QLineEdit.Normal)
        else:
            self._key_input.setEchoMode(QLineEdit.Password)

    def _save_key(self):
        raw = self._key_input.text().strip()
        if not raw:
            QMessageBox.warning(self, "", t("key_empty"))
            return
        self.config.api_key = raw
        self._stored_key = raw
        save_config(self.config)
        self.client = DeepSeekClient(raw)
        QMessageBox.information(self, "", t("key_saved"))
        if self.config.show_taskbar_widget and HAS_TW:
            if self._tw and self._tw.is_alive():
                self._tw.update_client(raw)
            else:
                self._start_tw()
        self._refresh()

    def _save_interval(self):
        try:
            v = int(self._cmb_interval.currentText())
            self.config.refresh_interval = v
            save_config(self.config)
            self._schedule()
            if self._tw and self._tw.is_alive():
                self._tw.update_interval(v)
        except ValueError:
            pass

    def _on_theme_change(self, mode: str):
        self.config.theme_mode = mode
        save_config(self.config)
        set_theme_mode(mode)
        # Clear ALL inline stylesheets from child widgets so global QSS
        # can take effect. Then re-set only the critical dynamic ones.
        self._clear_child_stylesheets(self)
        self.setStyleSheet(build_stylesheet())
        self._refresh_dynamic_styles()

    def _clear_child_stylesheets(self, parent):
        """Recursively clear inline stylesheets from all child widgets."""
        for child in parent.findChildren(QWidget):
            if child is not parent:
                child.setStyleSheet("")

    def _refresh_dynamic_styles(self):
        """Re-apply inline styles that global QSS doesn't cover."""
        c = C
        # Header bar
        hdr = self.centralWidget().layout().itemAt(0).widget()
        if hdr:
            hdr.setStyleSheet(f"background-color: {c['header']}; border-bottom: 2px solid {c['accent']};")
        # Title label (font+color)
        self._lbl_title.setStyleSheet(
            f"font-weight: bold; font-size: 20pt; color: {c['text']}; border: none; background: transparent;")
        # Status label
        self._lbl_status.setStyleSheet(
            f"color: {c['text2']}; font-size: 9pt; border: none; background: transparent;")
        # History stats labels
        for lbl in [self._lbl_hist_start, self._lbl_hist_curr]:
            lbl.setStyleSheet(f"color: {c['text2']}; font-size: 9pt;")
        # Pricing text label
        self._lbl_pricing.setStyleSheet(
            f"font-family: Consolas; font-size: 10pt; color: {c['text2']}; "
            f"border: none; background: transparent;")
        # Projected days label
        self._lbl_projected.setStyleSheet(
            f"color: {c['text']}; font-size: 10pt; border: none; background: transparent;")
        # About label
        self._lbl_about.setStyleSheet(
            f"color: {c['text2']}; font-size: 10pt; border: none; background: transparent; word-wrap: break-word;")
        # Theme buttons
        mode = get_theme_mode()
        for key, btn in self._theme_btns.items():
            active = key == mode
            btn.setStyleSheet(
                f"background-color: {c['accent'] if active else c['btn']}; "
                f"color: white; border: none; border-radius: 4px; padding: 4px 12px;")
        # Range selector buttons
        if hasattr(self, "_range_sel"):
            for btn in self._range_sel._buttons.values():
                btn.style().unpolish(btn)
                btn.style().polish(btn)
        # Chart
        if hasattr(self, "_chart"):
            self._chart.update()
        # Hint labels in settings — restore text2 color via QSS-re-applied parents (no-op: global QSS handles QLabel)
        # Balance data colors
        if self._last_data:
            self._display_balance(self._last_data)

    def _toggle_auto_start(self):
        enabled = self._cb_auto_start.isChecked()
        self.config.auto_start = enabled
        save_config(self.config)
        self._set_auto_start_registry(enabled)

    def _tray_toggle_auto_start(self):
        self.config.auto_start = not self.config.auto_start
        save_config(self.config)
        self._set_auto_start_registry(self.config.auto_start)
        self._cb_auto_start.setChecked(self.config.auto_start)

    def _set_auto_start_registry(self, enabled: bool):
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0,
                                winreg.KEY_SET_VALUE) as key:
                if enabled:
                    exe = sys.executable if getattr(sys, "frozen", False) else sys.executable
                    winreg.SetValueEx(key, "DeepSeekMonitor", 0, winreg.REG_SZ, exe)
                else:
                    try: winreg.DeleteValue(key, "DeepSeekMonitor")
                    except FileNotFoundError: pass
        except Exception:
            logger.exception("Failed to update auto-start registry")

    # ── Run ──────────────────────────────────────────────────────────────────

    @classmethod
    def run(cls):
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        config = load_config()
        AppGlobals.lang = config.language
        window = cls(config)
        window.show()
        app.exec()
