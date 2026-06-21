"""Theme constants and QSS stylesheet for DeepSeek Monitor.

Supports light/dark themes that follow the Windows system setting.
"""

import logging
import sys

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
#  Color Palettes
# ══════════════════════════════════════════════════════════════════════════════

_DARK = {
    "bg": "#0f1119",
    "bg2": "#1a1d2e",
    "bg3": "#13151f",
    "card": "#1e2133",
    "card_border": "#2a2d3e",
    "header": "#13151f",
    "accent": "#6366f1",
    "accent_h": "#818cf8",
    "green": "#34d399",
    "yellow": "#fbbf24",
    "red": "#f87171",
    "blue": "#60a5fa",
    "text": "#e2e8f0",
    "text2": "#64748b",
    "border": "#2a2d3e",
    "btn": "#1e2133",
    "btn_h": "#2a2d3e",
    "chart_bg": "#1a1d2e",
}

_LIGHT = {
    "bg": "#f1f5f9",
    "bg2": "#e2e8f0",
    "bg3": "#cbd5e1",
    "card": "#ffffff",
    "card_border": "#e2e8f0",
    "header": "#ffffff",
    "accent": "#4f46e5",
    "accent_h": "#6366f1",
    "green": "#10b981",
    "yellow": "#d97706",
    "red": "#ef4444",
    "blue": "#3b82f6",
    "text": "#1e293b",
    "text2": "#64748b",
    "border": "#e2e8f0",
    "btn": "#f1f5f9",
    "btn_h": "#e2e8f0",
    "chart_bg": "#f8fafc",
}


def _detect_system_theme() -> bool:
    """Return True if Windows uses light theme."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
            v, _ = winreg.QueryValueEx(k, "SystemUsesLightTheme")
            return v == 1
    except Exception:
        return False


# Global palette
_mode = "system"
_is_light = _detect_system_theme()
C = dict(_LIGHT if _is_light else _DARK)


def set_theme_mode(mode: str):
    """Set theme mode: 'light', 'dark', or 'system'."""
    global _mode, _is_light
    _mode = mode
    if mode == "light":
        _is_light = True
    elif mode == "dark":
        _is_light = False
    else:  # system
        _is_light = _detect_system_theme()
    C.clear()
    C.update(_LIGHT if _is_light else _DARK)


def refresh_system_theme():
    """Re-detect system theme (called when mode is 'system')."""
    global _mode, _is_light
    if _mode != "system":
        return
    new_light = _detect_system_theme()
    if new_light != _is_light:
        _is_light = new_light
        C.clear()
        C.update(_LIGHT if _is_light else _DARK)
        return True
    return False


def get_theme_mode() -> str:
    return _mode


def is_light() -> bool:
    return _is_light

# ══════════════════════════════════════════════════════════════════════════════
#  Fonts
# ══════════════════════════════════════════════════════════════════════════════
F = {
    "title":     "font: 22pt 'Segoe UI'; font-weight: bold;",
    "balance":   "font: 36pt 'Consolas'; font-weight: bold;",
    "section":   "font: 13pt 'Segoe UI'; font-weight: bold;",
    "body":      "font: 10pt 'Segoe UI';",
    "small":     "font: 9pt 'Segoe UI';",
    "mono":      "font: 10pt 'Consolas';",
    "mono_big":  "font: 40pt 'Consolas'; font-weight: bold;",
}


# ══════════════════════════════════════════════════════════════════════════════
#  QSS Generator
# ══════════════════════════════════════════════════════════════════════════════

def build_stylesheet() -> str:
    c = C
    return f"""
/* ── Main Window ─────────────────────────────────── */
QMainWindow {{
    background-color: {c["bg"]};
    color: {c["text"]};
}}
QWidget {{
    background-color: {c["bg"]};
    color: {c["text"]};
}}

/* ── Tab Widget ──────────────────────────────────── */
QTabWidget::pane {{
    border: none;
    background-color: {c["bg"]};
}}
QTabBar::tab {{
    background-color: {c["bg2"]};
    color: {c["text"]};
    padding: 8px 20px;
    border: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
    font-size: 10pt;
}}
QTabBar::tab:selected {{
    background-color: {c["accent"]};
    color: white;
}}

/* ── Buttons ─────────────────────────────────────── */
QPushButton {{
    background-color: {c["btn"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {c["btn_h"]};
    border-color: {c["accent"]};
}}
QPushButton#accentBtn {{
    background-color: {c["accent"]};
    color: white;
    border: none;
}}
QPushButton#accentBtn:hover {{
    background-color: {c["accent_h"]};
}}
QPushButton#rangeBtn {{
    border-radius: 4px;
    padding: 4px 12px;
    background-color: {c["btn"]};
    color: {c["text"]};
    border: none;
    font-size: 9pt;
}}
QPushButton#rangeBtn:checked {{
    background-color: {c["accent"]};
    color: white;
}}
QPushButton#rangeBtn:hover {{
    background-color: {c["btn_h"]};
}}

/* ── GlassCard ────────────────────────────────────── */
QFrame#glassCard {{
    background-color: {c["card"]};
    border: 1px solid {c["card_border"]};
    border-radius: 12px;
}}

/* ── StatCard ─────────────────────────────────────── */
QLabel#statValue {{
    font: 22pt 'Consolas'; font-weight: bold;
    color: {c["accent"]};
}}
QLabel#statLabel {{
    font: 9pt 'Segoe UI';
    color: {c["text2"]};
}}
QLabel#sectionTitle {{
    font: 13pt 'Segoe UI'; font-weight: bold;
    color: {c["accent"]};
}}
QLabel#titleLabel {{
    font: 20pt 'Segoe UI'; font-weight: bold;
    color: {c["text"]};
}}

/* ── CollapsibleSection ──────────────────────────── */
QFrame#collapsibleHeader {{
    background-color: {c["card"]};
    border: 1px solid {c["card_border"]};
    border-radius: 8px;
}}
QFrame#collapsibleHeader:hover {{
    border-color: {c["accent"]};
}}
QFrame#collapsibleContent {{
    background-color: {c["card"]};
    border: 1px solid {c["card_border"]};
    border-top: none;
    border-radius: 0 0 8px 8px;
}}
QLabel#arrowLabel {{
    color: {c["text2"]};
    font-size: 10pt;
    border: none;
    background: transparent;
}}
QLabel#collapsibleTitle {{
    color: {c["text"]};
    font-size: 11pt;
    font-weight: bold;
    border: none;
    background: transparent;
}}
QLabel#collapsibleStatus {{
    color: {c["text2"]};
    font-size: 9pt;
    border: none;
    background: transparent;
}}

/* ── Inputs ───────────────────────────────────────── */
QLineEdit {{
    background-color: {c["bg3"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    padding: 6px 10px;
    font-family: Consolas;
    font-size: 10pt;
}}
QLineEdit:focus {{
    border-color: {c["accent"]};
}}
QComboBox {{
    background-color: {c["bg3"]};
    color: {c["text"]};
    border: 1px solid {c["border"]};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 10pt;
}}
QComboBox:hover {{
    border-color: {c["accent"]};
}}
QComboBox QAbstractItemView {{
    background-color: {c["bg3"]};
    color: {c["text"]};
    selection-background-color: {c["accent"]};
    border: 1px solid {c["border"]};
}}
QCheckBox {{
    color: {c["text"]};
    spacing: 8px;
    font-size: 10pt;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {c["border"]};
    background-color: {c["bg3"]};
}}
QCheckBox::indicator:checked {{
    background-color: {c["accent"]};
    border-color: {c["accent"]};
}}

/* ── Scroll ───────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: {c["bg"]};
}}
QScrollArea > QWidget > QWidget {{
    background-color: {c["bg"]};
}}
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {c["border"]};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {c["btn_h"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ── Misc Labels ─────────────────────────────────── */
QLabel {{
    background-color: transparent;
    border: none;
    color: {c["text"]};
}}
"""
