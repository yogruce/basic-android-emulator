"""Win32 pencere API'leri (doğru argtypes/restype tanımlarıyla, 64-bit güvenli)."""

import ctypes
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

LONG_PTR = ctypes.c_ssize_t
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.MoveWindow.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.MoveWindow.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.SetParent.argtypes = [wintypes.HWND, wintypes.HWND]
user32.SetParent.restype = wintypes.HWND
user32.SetFocus.argtypes = [wintypes.HWND]
user32.SetFocus.restype = wintypes.HWND
user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
user32.SetWindowLongPtrW.restype = LONG_PTR
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

GWL_STYLE = -16
GWL_EXSTYLE = -20
GWLP_HWNDPARENT = -8

WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_SYSMENU = 0x00080000
WS_MINIMIZEBOX = 0x00020000
WS_MAXIMIZEBOX = 0x00010000
WS_CLIPSIBLINGS = 0x04000000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080

SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4


def _to_signed(value: int) -> int:
    """Stil bitlerini LONG_PTR için işaretli tamsayıya çevirir."""
    value &= (1 << (8 * ctypes.sizeof(LONG_PTR))) - 1
    if value >= 1 << (8 * ctypes.sizeof(LONG_PTR) - 1):
        value -= 1 << (8 * ctypes.sizeof(LONG_PTR))
    return value


def window_title(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def find_windows_by_pid(pid: int, title: str = None) -> list:
    """Belirtilen sürece ait görünür üst düzey pencereleri döndürür."""
    found = []

    @EnumWindowsProc
    def _cb(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            if title is None or window_title(hwnd) == title:
                found.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return found


def is_window(hwnd) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


def window_rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right - r.left, r.bottom - r.top


def client_size(hwnd):
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    return r.right - r.left, r.bottom - r.top


def cursor_pos():
    p = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def embed_as_child(hwnd, parent_hwnd, width: int, height: int) -> bool:
    """Harici pencereyi gerçek bir alt pencere (WS_CHILD) olarak parent içine gömer."""
    style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
    style &= ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX)
    style |= WS_CHILD | WS_VISIBLE | WS_CLIPSIBLINGS
    user32.SetWindowLongPtrW(hwnd, GWL_STYLE, _to_signed(style))
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, _to_signed(ex & ~WS_EX_APPWINDOW))
    if not user32.SetParent(hwnd, parent_hwnd):
        return False
    user32.SetWindowPos(hwnd, None, 0, 0, width, height, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
    return True


def make_owned_tool_window(hwnd, owner_hwnd) -> None:
    """Overlay modu: pencereyi ana pencereye 'sahiplenir' ve görev çubuğundan gizler."""
    user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, _to_signed(int(owner_hwnd)))
    ex = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, _to_signed((ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW))


def move_window(hwnd, x: int, y: int, w: int, h: int) -> None:
    user32.MoveWindow(hwnd, x, y, w, h, True)


def show_window(hwnd, visible: bool) -> None:
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE if visible else SW_HIDE)


def set_focus(hwnd) -> None:
    user32.SetFocus(hwnd)


user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short
user32.GetFocus.argtypes = []
user32.GetFocus.restype = wintypes.HWND


def mouse_button_down() -> bool:
    """Sol veya sağ fare tuşu şu an basılı mı?"""
    return bool(user32.GetAsyncKeyState(0x01) & 0x8000) or bool(user32.GetAsyncKeyState(0x02) & 0x8000)
