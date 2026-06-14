"""
Windows Taskbar Widget — DeepSeek Balance Display ONLY.

LiteMonitor approach: SetParent + LWA_COLORKEY.
Single metric: account balance.
"""

import ctypes
import ctypes.wintypes
import threading
import logging
from typing import Optional

from src.api import DeepSeekClient, DeepSeekAPIError

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  Win32 Constants
# ══════════════════════════════════════════════════════════════════════════════

GWL_STYLE   = -16
GWL_EXSTYLE = -20

WS_CHILD        = 0x40000000
WS_VISIBLE      = 0x10000000
WS_CLIPSIBLINGS = 0x04000000
WS_POPUP        = 0x80000000

WS_EX_LAYERED    = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000

LWA_COLORKEY = 0x00000001

SWP_NOZORDER    = 0x0004
SWP_NOACTIVATE  = 0x0010
SWP_SHOWWINDOW  = 0x0040

WM_PAINT        = 0x000F
WM_TIMER        = 0x0113
WM_CLOSE        = 0x0010
WM_DESTROY      = 0x0002
WM_ERASEBKGND   = 0x0014

TRANSPARENT_MODE = 1
DT_LEFT       = 0x00000001
DT_VCENTER    = 0x00000004
DT_SINGLELINE = 0x00000020


# ══════════════════════════════════════════════════════════════════════════════
#  Structures
# ══════════════════════════════════════════════════════════════════════════════

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class PAINTSTRUCT(ctypes.Structure):
    _fields_ = [
        ("hdc", ctypes.wintypes.HDC), ("fErase", ctypes.wintypes.BOOL),
        ("rcPaint", RECT), ("fRestore", ctypes.wintypes.BOOL),
        ("fIncUpdate", ctypes.wintypes.BOOL), ("rgbReserved", ctypes.c_byte * 32),
    ]


class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint), ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p), ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int), ("hInstance", ctypes.wintypes.HINSTANCE),
        ("hIcon", ctypes.wintypes.HICON), ("hCursor", ctypes.wintypes.HANDLE),
        ("hbrBackground", ctypes.wintypes.HBRUSH),
        ("lpszMenuName", ctypes.wintypes.LPCWSTR),
        ("lpszClassName", ctypes.wintypes.LPCWSTR), ("hIconSm", ctypes.wintypes.HICON),
    ]


# ══════════════════════════════════════════════════════════════════════════════
#  Win32 bindings
# ══════════════════════════════════════════════════════════════════════════════

user32   = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32    = ctypes.windll.gdi32

FindWindowW     = user32.FindWindowW
FindWindowExW   = user32.FindWindowExW
SetParent       = user32.SetParent
GetWindowRect   = user32.GetWindowRect
GetClientRect   = user32.GetClientRect
SetWindowPos    = user32.SetWindowPos
InvalidateRect  = user32.InvalidateRect
SetTimer        = user32.SetTimer
KillTimer       = user32.KillTimer
SetLayeredWindowAttributes = user32.SetLayeredWindowAttributes
RegisterClassExW = user32.RegisterClassExW
CreateWindowExW  = user32.CreateWindowExW
DestroyWindow    = user32.DestroyWindow
GetMessageW      = user32.GetMessageW
TranslateMessage = user32.TranslateMessage
DispatchMessageW = user32.DispatchMessageW
PostMessageW     = user32.PostMessageW
BeginPaint   = user32.BeginPaint
EndPaint     = user32.EndPaint
FillRect     = user32.FillRect
DrawTextW    = user32.DrawTextW

# 64-bit safe window long
try:
    _SetWindowLongPtr = user32.SetWindowLongPtrW
    _GetWindowLongPtr = user32.GetWindowLongPtrW
except AttributeError:
    _SetWindowLongPtr = user32.SetWindowLongW
    _GetWindowLongPtr = user32.GetWindowLongW
_SetWindowLongPtr.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
_SetWindowLongPtr.restype  = ctypes.c_ssize_t
_GetWindowLongPtr.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
_GetWindowLongPtr.restype  = ctypes.c_ssize_t

DefWindowProcW = user32.DefWindowProcW
DefWindowProcW.argtypes = [
    ctypes.wintypes.HWND, ctypes.wintypes.UINT,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
DefWindowProcW.restype = ctypes.c_ssize_t

CreateFontW       = gdi32.CreateFontW
SelectObject      = gdi32.SelectObject
DeleteObject      = gdi32.DeleteObject
SetTextColor      = gdi32.SetTextColor
SetBkMode         = gdi32.SetBkMode
CreateSolidBrush  = gdi32.CreateSolidBrush


# ══════════════════════════════════════════════════════════════════════════════
#  TaskbarWidget — shows ONLY the balance on the taskbar
# ══════════════════════════════════════════════════════════════════════════════

class TaskbarWidget:
    """
    Minimal balance-only taskbar widget.

    Embeds into Shell_TrayWnd via SetParent + LWA_COLORKEY.
    Shows: Label ("DS") + Balance value (¥xxx.xx).
    """

    TIMER_ID    = 4001
    TIMER_FAST  = 4002
    THEME_TIMER = 4003
    _instance_counter = 0

    # BGR colors
    C_GREEN  = 0x66FF99
    C_YELLOW = 0x66D6FF
    C_RED    = 0x6666FF
    C_WHITE  = 0xFFFFFF
    C_GRAY   = 0x999999
    C_LABEL  = 0x808080

    TRANS_DARK  = 0x292828
    TRANS_LIGHT = 0xD3D2D2

    THEME_CHECK_SECONDS = 5  # how often to re-check Windows theme

    def __init__(self, api_key: str, label: str = "Balance",
                 refresh_seconds: int = 60, position: str = "right"):
        TaskbarWidget._instance_counter += 1
        self._wnd_class = f"DSBalance_{TaskbarWidget._instance_counter}"
        self.api_key          = api_key
        self.label            = label        # top label text (i18n)
        self.refresh_seconds  = refresh_seconds
        self.position         = position

        self._hwnd: Optional[int] = None
        self._h_taskbar: Optional[int] = None
        self._h_tray: Optional[int] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._cb_ref  = None

        self._is_light   = False
        self._trans_key  = self.TRANS_DARK
        self._embedded   = False   # track whether SetParent succeeded
        self._last_taskbar: Optional[int] = None  # detect explorer restart

        self._value = "..."
        self._color = self.C_GRAY

        self._hfont_l = None
        self._hfont_v = None

        self._destroyed = False       # prevent double-destroy
        self._fetch_lock = threading.Lock()  # prevent concurrent API calls

        self._client = DeepSeekClient(api_key)

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._destroyed = False
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the widget to close cleanly."""
        self._running = False
        if self._hwnd and not self._destroyed:
            PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def stop_and_wait(self, timeout: float = 3.0):
        """Stop and wait for the background thread to finish."""
        self.stop()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=timeout)

    def is_alive(self) -> bool:
        return self._running and self._hwnd is not None

    # ── Thread ────────────────────────────────────────────────────────────────

    def _run(self):
        self._detect_theme()
        self._find_handles()
        self._create_fonts()
        self._create_window()
        if not self._hwnd:
            self._running = False
            return
        self._embed()
        self._position()
        self._fetch()
        SetTimer(self._hwnd, self.TIMER_FAST, 4000, None)
        SetTimer(self._hwnd, self.TIMER_ID, self.refresh_seconds * 1000, None)
        SetTimer(self._hwnd, self.THEME_TIMER, self.THEME_CHECK_SECONDS * 1000, None)
        self._loop()
        self._cleanup()

    # ── Theme ─────────────────────────────────────────────────────────────────

    def _detect_theme(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                v, _ = winreg.QueryValueEx(k, "SystemUsesLightTheme")
                self._is_light = (v == 1)
        except Exception:
            self._is_light = False
        self._trans_key = self.TRANS_LIGHT if self._is_light else self.TRANS_DARK

    # ── Taskbar handles ───────────────────────────────────────────────────────

    def _find_handles(self):
        old_taskbar = self._h_taskbar
        self._h_taskbar = FindWindowW("Shell_TrayWnd", None)
        self._h_tray = (
            FindWindowExW(self._h_taskbar, 0, "TrayNotifyWnd", None)
            if self._h_taskbar else None
        )
        # Detect explorer restart / handle change
        if old_taskbar and old_taskbar != self._h_taskbar:
            logger.info("Taskbar handle changed (%s → %s) — will re-embed",
                        old_taskbar, self._h_taskbar)
            self._embedded = False

    # ── GDI fonts ─────────────────────────────────────────────────────────────

    def _create_fonts(self):
        self._hfont_l = CreateFontW(13, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI")
        self._hfont_v = CreateFontW(15, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Consolas")

    # ── Window creation ───────────────────────────────────────────────────────

    def _create_window(self):
        hinst = kernel32.GetModuleHandleW(None)
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t,
            ctypes.wintypes.HWND, ctypes.wintypes.UINT,
            ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM)
        self._cb_ref = WNDPROC(self._wnd_proc)

        wc = WNDCLASSEX()
        wc.cbSize = ctypes.sizeof(WNDCLASSEX)
        wc.lpfnWndProc = ctypes.cast(self._cb_ref, ctypes.c_void_p)
        wc.hInstance = hinst
        wc.lpszClassName = self._wnd_class
        wc.hbrBackground = 0
        RegisterClassExW(ctypes.byref(wc))

        self._hwnd = CreateWindowExW(
            WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
            self._wnd_class, "DSBalance", WS_POPUP,
            0, 0, 200, 40, None, None, hinst, None)

    # ── Embed into taskbar ────────────────────────────────────────────────────

    def _embed(self):
        """Embed the widget window into the taskbar via SetParent."""
        if not self._h_taskbar or not self._hwnd:
            return
        SetParent(self._hwnd, self._h_taskbar)

        s = _GetWindowLongPtr(self._hwnd, GWL_STYLE)
        s = (s & ~WS_POPUP) | WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS
        _SetWindowLongPtr(self._hwnd, GWL_STYLE, s)

        ex = _GetWindowLongPtr(self._hwnd, GWL_EXSTYLE)
        ex |= WS_EX_LAYERED
        _SetWindowLongPtr(self._hwnd, GWL_EXSTYLE, ex)

        SetLayeredWindowAttributes(self._hwnd, self._trans_key, 0, LWA_COLORKEY)

        self._embedded = True
        self._last_taskbar = self._h_taskbar

    # ── Position ──────────────────────────────────────────────────────────────

    def _position(self):
        if not self._h_taskbar or not self._hwnd:
            return

        tb = RECT()
        GetWindowRect(self._h_taskbar, ctypes.byref(tb))
        tb_w = tb.right - tb.left
        tb_h = tb.bottom - tb.top

        widget_w = 160
        widget_h = max(tb_h, 32)

        tray_left = tb.right - 120
        if self._h_tray:
            tr = RECT()
            GetWindowRect(self._h_tray, ctypes.byref(tr))
            tray_left = tr.left

        if tb_w > tb_h:
            x = (tray_left - widget_w - 6) if self.position == "right" else (tb.left + 6)
            y = 0
        else:
            x = 0
            y = 6

        SetWindowPos(self._hwnd, 0, x, y, widget_w, widget_h,
                     SWP_NOZORDER | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def _paint(self):
        ps = PAINTSTRUCT()
        hdc = BeginPaint(self._hwnd, ctypes.byref(ps))
        if not hdc:
            return

        cr = RECT()
        GetClientRect(self._hwnd, ctypes.byref(cr))
        w = cr.right - cr.left
        h = cr.bottom - cr.top

        # Transparent background
        br = CreateSolidBrush(self._trans_key)
        FillRect(hdc, ctypes.byref(cr), br)
        DeleteObject(br)
        SetBkMode(hdc, TRANSPARENT_MODE)

        half = h // 2

        # Label (top)
        lr = RECT(8, 2, w - 4, half + 2)
        SetTextColor(hdc, self.C_LABEL)
        SelectObject(hdc, self._hfont_l)
        DrawTextW(hdc, self.label, len(self.label), ctypes.byref(lr),
                  DT_LEFT | DT_VCENTER | DT_SINGLELINE)

        # Value (bottom)
        vr = RECT(8, half - 1, w - 4, h - 1)
        SetTextColor(hdc, self._color)
        SelectObject(hdc, self._hfont_v)
        DrawTextW(hdc, self._value, len(self._value), ctypes.byref(vr),
                  DT_LEFT | DT_VCENTER | DT_SINGLELINE)

        EndPaint(self._hwnd, ctypes.byref(ps))

    # ── Fetch ─────────────────────────────────────────────────────────────────

    def _fetch(self):
        """Schedule a fetch if one is not already in progress."""
        if self._fetch_lock.locked():
            return  # skip if a fetch is already running
        threading.Thread(target=self._do_fetch, daemon=True).start()

    def _do_fetch(self):
        """Use DeepSeekClient for consistent error handling."""
        if not self._fetch_lock.acquire(blocking=False):
            return
        try:
            data = self._client.get_balance()
            infos = data.get("balance_infos", [])
            if infos:
                b = infos[0]
                total = float(b.get("total_balance", 0))
                sym = "$" if b.get("currency") == "USD" else "¥"
                self._value = f"{sym}{total:.2f}"
                if total > 20:
                    self._color = self.C_GREEN
                elif total > 5:
                    self._color = self.C_YELLOW
                else:
                    self._color = self.C_RED
            else:
                self._value = "N/A"
                self._color = self.C_GRAY
        except DeepSeekAPIError:
            self._value = "Error"
            self._color = self.C_RED
        except Exception:
            logger.exception("Unexpected error in taskbar widget fetch")
            self._value = "Error"
            self._color = self.C_RED
        finally:
            self._fetch_lock.release()

        if self._hwnd:
            InvalidateRect(self._hwnd, None, True)

    # ── Message loop ──────────────────────────────────────────────────────────

    def _loop(self):
        msg = ctypes.wintypes.MSG()
        while GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            TranslateMessage(ctypes.byref(msg))
            DispatchMessageW(ctypes.byref(msg))

    def _wnd_proc(self, hwnd, msg, w, l):
        if msg == WM_PAINT:
            self._paint()
            return 0
        if msg == WM_TIMER:
            if w == self.TIMER_FAST:
                KillTimer(hwnd, self.TIMER_FAST)
            if w == self.THEME_TIMER:
                old = self._is_light
                self._detect_theme()
                if self._is_light != old:
                    SetLayeredWindowAttributes(hwnd, self._trans_key, 0, LWA_COLORKEY)
                return 0
            self._find_handles()
            # Re-embed if taskbar handle changed (explorer restart)
            if not self._embedded or self._h_taskbar != self._last_taskbar:
                self._embed()
            self._position()
            self._fetch()
            return 0
        if msg == WM_ERASEBKGND:
            return 1
        if msg == WM_CLOSE:
            self._destroyed = True
            DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            KillTimer(hwnd, self.TIMER_ID)
            KillTimer(hwnd, self.TIMER_FAST)
            KillTimer(hwnd, self.THEME_TIMER)
            return 0
        return DefWindowProcW(hwnd, msg, w, l)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _cleanup(self):
        self._destroyed = True
        self._embedded = False
        if self._hwnd:
            try: SetParent(self._hwnd, None)
            except: pass
        if self._hfont_l: DeleteObject(self._hfont_l); self._hfont_l = None
        if self._hfont_v: DeleteObject(self._hfont_v); self._hfont_v = None
        self._hwnd = self._h_taskbar = self._h_tray = None
        self._running = False
