"""
System Tray icon for Windows — zero-dependency Win32 Shell_NotifyIcon implementation.
Requires: ctypes (built-in), PIL (for icon image generation).
"""

import ctypes
import ctypes.wintypes
import logging
from typing import Callable, Optional
import threading

logger = logging.getLogger(__name__)


# ─── Win32 Constants ──────────────────────────────────────────────────────────

NIM_ADD         = 0x00000000
NIM_MODIFY      = 0x00000001
NIM_DELETE      = 0x00000002
NIF_MESSAGE     = 0x00000001
NIF_ICON        = 0x00000002
NIF_TIP         = 0x00000004
NIF_INFO        = 0x00000010

WM_USER          = 0x0400
WM_TRAYICON      = WM_USER + 1
WM_COMMAND       = 0x0111
WM_CLOSE         = 0x0010
WM_DESTROY       = 0x0002
WM_LBUTTONUP     = 0x0202
WM_RBUTTONUP     = 0x0205
WM_LBUTTONDBLCLK = 0x0203

WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TOPMOST    = 0x00000008
GWL_EXSTYLE      = -20
SW_HIDE           = 0
SW_SHOW           = 5

MF_STRING    = 0x00000000
MF_SEPARATOR = 0x00000800
MF_CHECKED   = 0x00000008
TPM_BOTTOMALIGN = 0x0020
TPM_LEFTALIGN   = 0x0000
TPM_RIGHTBUTTON = 0x0002

IDI_APPLICATION = 32512
IMAGE_ICON      = 1
LR_DEFAULTSIZE  = 0x00000040
LR_LOADFROMFILE = 0x00000010


# ─── Structures ───────────────────────────────────────────────────────────────

class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize",           ctypes.wintypes.DWORD),
        ("hWnd",             ctypes.wintypes.HWND),
        ("uID",              ctypes.wintypes.UINT),
        ("uFlags",           ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon",            ctypes.wintypes.HICON),
        ("szTip",            ctypes.c_wchar * 128),
        ("dwState",          ctypes.wintypes.DWORD),
        ("dwStateMask",      ctypes.wintypes.DWORD),
        ("szInfo",           ctypes.c_wchar * 256),
        ("uTimeout",         ctypes.wintypes.UINT),
        ("szInfoTitle",      ctypes.c_wchar * 64),
        ("dwInfoFlags",      ctypes.wintypes.DWORD),
        ("guidItem",         ctypes.c_byte * 16),
        ("hBalloonIcon",     ctypes.wintypes.HICON),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd",    ctypes.wintypes.HWND),
        ("message", ctypes.wintypes.UINT),
        ("wParam",  ctypes.wintypes.WPARAM),
        ("lParam",  ctypes.wintypes.LPARAM),
        ("time",    ctypes.wintypes.DWORD),
        ("pt",      POINT),
    ]


class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize",        ctypes.c_uint),
        ("style",         ctypes.c_uint),
        ("lpfnWndProc",   ctypes.c_void_p),
        ("cbClsExtra",    ctypes.c_int),
        ("cbWndExtra",    ctypes.c_int),
        ("hInstance",     ctypes.wintypes.HINSTANCE),
        ("hIcon",         ctypes.wintypes.HICON),
        ("hCursor",       ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName",  ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ("hIconSm",       ctypes.wintypes.HICON),
    ]


# ─── Win32 DLL bindings ──────────────────────────────────────────────────────

user32  = ctypes.windll.user32
shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

Shell_NotifyIconW = shell32.Shell_NotifyIconW
CreateWindowExW    = user32.CreateWindowExW
DefWindowProcW     = user32.DefWindowProcW
DefWindowProcW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
DefWindowProcW.restype = ctypes.c_ssize_t
DestroyWindow      = user32.DestroyWindow
GetMessageW        = user32.GetMessageW
TranslateMessage   = user32.TranslateMessage
DispatchMessageW   = user32.DispatchMessageW
PostMessageW       = user32.PostMessageW
RegisterClassW     = user32.RegisterClassW
DestroyIcon        = user32.DestroyIcon
LoadIconW          = user32.LoadIconW
LoadImageW         = user32.LoadImageW
SetForegroundWindow = user32.SetForegroundWindow
TrackPopupMenu     = user32.TrackPopupMenu
CreatePopupMenu    = user32.CreatePopupMenu
AppendMenuW        = user32.AppendMenuW
DestroyMenu        = user32.DestroyMenu
GetCursorPos       = user32.GetCursorPos
GetWindowLongW     = user32.GetWindowLongW
SetWindowLongW     = user32.SetWindowLongW
ShowWindow         = user32.ShowWindow


# ─── Balloon tip helper ───────────────────────────────────────────────────────

def _show_balloon(hwnd: int, title: str, msg: str, timeout_ms: int = 3000):
    """Show a balloon notification via Shell_NotifyIcon."""
    nid = NOTIFYICONDATA()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
    nid.hWnd   = hwnd
    nid.uID    = 1
    nid.uFlags = NIF_INFO
    nid.szInfoTitle = title
    nid.szInfo      = msg
    nid.dwInfoFlags = 0x01  # NIIF_INFO (info icon)
    nid.uTimeout    = timeout_ms
    Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))


# ─── TrayIcon class ───────────────────────────────────────────────────────────

class TrayIcon:
    """
    Windows system-tray icon.

    Usage:
        tray = TrayIcon(tooltip="My App", on_show=show_main, on_quit=quit_app)
        tray.start()      # blocking, runs in current thread
        tray.start_bg()   # non-blocking, runs in a daemon thread
        tray.update_tooltip("New text")
        tray.show_balloon("Title", "Message body")
        tray.stop()
    """

    TRAY_ICON_ID = 1
    WND_CLASS    = "DeepSeekMonitorTray"

    def __init__(
        self,
        tooltip: str = "DeepSeek Monitor",
        icon_path: Optional[str] = None,
        on_left_double_click: Optional[Callable] = None,
        on_right_click: Optional[Callable] = None,
        menu_items: Optional[list] = None,
    ):
        self.tooltip    = tooltip
        self.icon_path  = icon_path
        self.on_left_double_click = on_left_double_click
        self.on_right_click       = on_right_click
        self.menu_items = menu_items or []   # list of (label, callback) tuples

        self._hwnd: Optional[int] = None
        self._hicon = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self):
        """Run the tray icon event loop (blocking)."""
        self._create_window()
        self._add_icon()
        self._message_loop()
        self._cleanup()

    def start_bg(self):
        """Run in a background daemon thread (non-blocking)."""
        self._running = True
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()

    def stop(self):
        """Request the tray icon to close."""
        self._running = False
        if self._hwnd:
            PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def update_tooltip(self, text: str):
        self.tooltip = text[:127]
        if self._hwnd:
            nid = NOTIFYICONDATA()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
            nid.hWnd   = self._hwnd
            nid.uID    = self.TRAY_ICON_ID
            nid.uFlags = NIF_TIP
            nid.szTip  = self.tooltip
            Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def show_balloon(self, title: str, msg: str, timeout_ms: int = 3000):
        if self._hwnd:
            _show_balloon(self._hwnd, title, msg, timeout_ms)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _create_window(self):
        """Create a hidden message-only window."""
        hinstance = kernel32.GetModuleHandleW(None)

        # Window procedure callback
        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.wintypes.HWND, ctypes.wintypes.UINT,
            ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
        )
        self._wnd_proc_cb = WNDPROC(self._wnd_proc)

        wc = WNDCLASSEX()
        wc.cbSize        = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc   = ctypes.cast(self._wnd_proc_cb, ctypes.c_void_p)
        wc.hInstance      = hinstance
        wc.lpszClassName  = self.WND_CLASS

        RegisterClassW(ctypes.byref(wc))

        self._hwnd = CreateWindowExW(
            WS_EX_TOOLWINDOW,
            self.WND_CLASS,
            "DeepSeekMonitor",
            0, 0, 0, 0, 0,
            None, None, hinstance, None,
        )

    def _load_icon(self) -> int:
        """Load icon from file, or fall back to default app icon."""
        if self.icon_path:
            hicon = LoadImageW(
                None, self.icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
            )
            if hicon:
                return hicon
        return LoadIconW(None, IDI_APPLICATION)

    def _add_icon(self):
        self._hicon = self._load_icon()
        nid = NOTIFYICONDATA()
        nid.cbSize           = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd             = self._hwnd
        nid.uID              = self.TRAY_ICON_ID
        nid.uFlags           = NIF_ICON | NIF_MESSAGE | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon            = self._hicon
        nid.szTip            = self.tooltip[:127]
        Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    def _remove_icon(self):
        nid = NOTIFYICONDATA()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        nid.hWnd   = self._hwnd
        nid.uID    = self.TRAY_ICON_ID
        Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    def _message_loop(self):
        msg = MSG()
        while GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))
        self._running = False

    def _show_context_menu(self):
        if not self.menu_items:
            return

        hmenu = CreatePopupMenu()
        idx = 0
        for item in self.menu_items:
            if item[0] == "-":
                AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
            else:
                label = item[0]
                flags = MF_STRING
                # Support optional third element: checked (bool or callable)
                if len(item) >= 3:
                    checked = item[2]() if callable(item[2]) else item[2]
                    if checked:
                        flags |= MF_CHECKED
                AppendMenuW(hmenu, flags, 1000 + idx, label)
                idx += 1

        pt = POINT()
        GetCursorPos(ctypes.byref(pt))
        SetForegroundWindow(self._hwnd)
        TrackPopupMenu(
            hmenu,
            TPM_BOTTOMALIGN | TPM_LEFTALIGN | TPM_RIGHTBUTTON,
            pt.x, pt.y, 0, self._hwnd, None,
        )
        DestroyMenu(hmenu)

    def _on_wm_trayicon(self, wparam, lparam):
        if lparam == WM_LBUTTONDBLCLK and self.on_left_double_click:
            self.on_left_double_click()
        elif lparam == WM_RBUTTONUP:
            if self.on_right_click:
                self.on_right_click()
            else:
                self._show_context_menu()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_TRAYICON:
            self._on_wm_trayicon(wparam, lparam)
            return 0
        elif msg == WM_COMMAND:
            item_id = wparam & 0xFFFF
            # Filter out separators to find the right callback
            non_sep = [it for it in self.menu_items if it[0] != "-"]
            idx = item_id - 1000
            if 0 <= idx < len(non_sep):
                item = non_sep[idx]
                cb = item[1] if len(item) >= 2 else None
                if cb:
                    cb()
            return 0
        elif msg == WM_CLOSE:
            DestroyWindow(hwnd)
            return 0
        elif msg == WM_DESTROY:
            self._remove_icon()
            return 0
        return DefWindowProcW(hwnd, msg, wparam, lparam)

    def _cleanup(self):
        if self._hicon:
            DestroyIcon(self._hicon)
            self._hicon = None
        self._hwnd = None
