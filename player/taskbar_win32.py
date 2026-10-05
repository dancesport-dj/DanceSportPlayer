"""The Win32 half of the taskbar mini player — raw ctypes, no dependencies.

Qt6 dropped QtWinExtras, and this machine has no pywin32, no comtypes and no
winrt, so the thumbnail toolbar has to be driven by hand: an ITaskbarList3
built through CoCreateInstance and called through its vtable by index.

Nothing Qt lives here and nothing here decides anything — player.taskbar owns the
state, this module only carries it across to the shell. Importing it on a Mac
raises, so the caller checks sys.platform first; that is the whole reason it is
a separate file.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":   # pragma: no cover - guarded by the caller
    raise ImportError("player.taskbar_win32 is Windows-only")

_ole32 = ctypes.windll.ole32
_user32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32

# ITaskbarList3 vtable slots, counted from IUnknown down through the three
# interface generations — the ONLY way to reach these methods without a type
# library. The order is fixed by shobjidl_core.h and can never be reshuffled.
# Only the thumb bar is used: the icon overlay and the progress fill were
# deliberately dropped, so nothing here runs on the playback tick.
_RELEASE = 2
_HR_INIT = 3
_THUMB_BAR_ADD = 15
_THUMB_BAR_UPDATE = 16
_SET_THUMBNAIL_TOOLTIP = 19

# THUMBBUTTONMASK / THUMBBUTTONFLAGS — we always send an icon and a tooltip.
_THB_ICON = 0x2
_THB_TOOLTIP = 0x4
_THB_FLAGS = 0x8
_THBF_ENABLED = 0x0
_THBF_DISABLED = 0x1

_CLSCTX_INPROC_SERVER = 1
_DIB_RGB_COLORS = 0
_SM_CXSMICON = 49


class _GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


_CLSID_TASKBAR_LIST = _GUID(0x56FDF344, 0xFD6D, 0x11D0,
                            (0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90))
_IID_TASKBAR_LIST3 = _GUID(0xEA1AFB91, 0x9E28, 0x4B86,
                           (0x90, 0xE9, 0x9E, 0x9F, 0x8A, 0x5E, 0xEF, 0xAF))


class _THUMBBUTTON(ctypes.Structure):
    """Natural alignment, not packed — shobjidl_core.h declares it plain, so
    the hIcon pointer sits on an 8-byte boundary with padding before it."""
    _fields_ = [("dwMask", wintypes.DWORD), ("iId", wintypes.UINT),
                ("iBitmap", wintypes.UINT), ("hIcon", ctypes.c_void_p),
                ("szTip", wintypes.WCHAR * 260), ("dwFlags", wintypes.DWORD)]


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


class _ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                ("yHotspot", wintypes.DWORD), ("hbmMask", ctypes.c_void_p),
                ("hbmColor", ctypes.c_void_p)]


class _MSG(ctypes.Structure):
    _fields_ = [("hwnd", ctypes.c_void_p), ("message", wintypes.UINT),
                ("wParam", ctypes.c_void_p), ("lParam", ctypes.c_void_p),
                ("time", wintypes.DWORD), ("pt_x", wintypes.LONG),
                ("pt_y", wintypes.LONG)]


def _method(ptr: int, slot: int, *argtypes):
    """The function at `slot` of the COM object's vtable, ready to call."""
    vtbl = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p))[0]
    fn = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[slot]
    proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)
    return proto(fn)


def small_icon_px() -> int:
    """The size the shell wants for both the thumb buttons and the overlay."""
    return _user32.GetSystemMetrics(_SM_CXSMICON) or 16


def button_created_message() -> int:
    """The message the shell posts once a window HAS a taskbar button — before
    it arrives, ThumbBarAddButtons has nothing to add the buttons to."""
    return _user32.RegisterWindowMessageW("TaskbarButtonCreated")


def msg_fields(message) -> tuple[int, int, int] | None:
    """(hwnd, message id, wParam) out of the void* Qt hands a native filter.

    The hwnd matters: the filter is installed on the whole application, so it
    also sees the messages of every OTHER top-level window the app opens."""
    try:
        msg = ctypes.cast(int(message), ctypes.POINTER(_MSG)).contents
    except (TypeError, ValueError):   # pragma: no cover - malformed pointer
        return None
    return (msg.hwnd or 0), msg.message, (msg.wParam or 0)


def create() -> int | None:
    """A live ITaskbarList3, or None where the shell will not give us one.

    CoInitializeEx is skipped: Qt has already put this thread into an STA for
    drag-and-drop, and initialising it a second time would only have to be
    balanced by an uninitialise we have no good place to make."""
    ptr = ctypes.c_void_p()
    hr = _ole32.CoCreateInstance(ctypes.byref(_CLSID_TASKBAR_LIST), None,
                                 _CLSCTX_INPROC_SERVER,
                                 ctypes.byref(_IID_TASKBAR_LIST3),
                                 ctypes.byref(ptr))
    if hr < 0 or not ptr.value:
        return None
    try:
        _method(ptr.value, _HR_INIT)(ptr.value)
    except OSError:   # pragma: no cover - shell refused
        release(ptr.value)
        return None
    return ptr.value


def release(tb: int) -> None:
    proto = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)
    vtbl = ctypes.cast(tb, ctypes.POINTER(ctypes.c_void_p))[0]
    proto(ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[_RELEASE])(tb)


def hicon_from_argb(pixels: bytes, w: int, h: int) -> int | None:
    """An HICON out of premultiplied top-down BGRA bytes.

    Qt6 took QPixmap.toWinHICON away, so the bitmap is built by hand: a 32-bit
    DIB section for the colour, a throwaway 1-bit mask (the alpha channel does
    the real masking), and CreateIconIndirect over the pair."""
    info = _BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    info.bmiHeader.biWidth = w
    info.bmiHeader.biHeight = -h      # negative → top-down, as QImage stores it
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0  # BI_RGB
    bits = ctypes.c_void_p()
    _gdi32.CreateDIBSection.restype = ctypes.c_void_p
    _user32.GetDC.restype = ctypes.c_void_p
    dc = _user32.GetDC(None)
    colour = _gdi32.CreateDIBSection(ctypes.c_void_p(dc), ctypes.byref(info),
                                     _DIB_RGB_COLORS, ctypes.byref(bits), None, 0)
    _user32.ReleaseDC(None, ctypes.c_void_p(dc))
    if not colour or not bits.value:
        return None
    ctypes.memmove(bits.value, pixels, min(len(pixels), w * h * 4))
    # An ALL-ZERO mask — "opaque everywhere", leaving the shading to the colour
    # bitmap's alpha. CreateBitmap with a NULL bits pointer leaves the mask
    # UNDEFINED, and a mask that happens to come up as ones hides the entire
    # glyph: buttons that are really there, showing nothing at all.
    stride = ((w + 15) // 16) * 2      # 1 bpp scanlines are WORD-aligned
    blank = bytes(stride * h)
    _gdi32.CreateBitmap.restype = ctypes.c_void_p
    mask = _gdi32.CreateBitmap(w, h, 1, 1, blank)
    ii = _ICONINFO(fIcon=True, xHotspot=0, yHotspot=0,
                   hbmMask=mask, hbmColor=colour)
    _user32.CreateIconIndirect.restype = ctypes.c_void_p
    icon = _user32.CreateIconIndirect(ctypes.byref(ii))
    # CreateIconIndirect copies both bitmaps, so ours go back straight away.
    _gdi32.DeleteObject(ctypes.c_void_p(colour))
    _gdi32.DeleteObject(ctypes.c_void_p(mask))
    return icon or None


def destroy_icon(icon: int) -> None:
    _user32.DestroyIcon(ctypes.c_void_p(icon))


def _thumb_array(buttons):
    arr = (_THUMBBUTTON * len(buttons))()
    for i, (ident, icon, tip, enabled) in enumerate(buttons):
        arr[i].dwMask = _THB_ICON | _THB_TOOLTIP | _THB_FLAGS
        arr[i].iId = ident
        arr[i].hIcon = icon
        arr[i].szTip = tip[:259]
        arr[i].dwFlags = _THBF_ENABLED if enabled else _THBF_DISABLED
    return arr


def _thumb_call(tb: int, slot: int, hwnd: int, buttons) -> int:
    """The raw HRESULT, not a bool: S_OK with nothing on screen is a real
    outcome here, and the only way to tell it from a refusal is the number."""
    arr = _thumb_array(buttons)
    vtbl = ctypes.cast(tb, ctypes.POINTER(ctypes.c_void_p))[0]
    fn = ctypes.cast(vtbl, ctypes.POINTER(ctypes.c_void_p))[slot]
    proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p,
                               wintypes.UINT, ctypes.POINTER(_THUMBBUTTON))
    return proto(fn)(tb, ctypes.c_void_p(hwnd), len(buttons), arr)


def add_buttons(tb: int, hwnd: int, buttons) -> int:
    """Install the toolbar. Only ever succeeds ONCE per window — every later
    change has to go through update_buttons."""
    return _thumb_call(tb, _THUMB_BAR_ADD, hwnd, buttons)


def update_buttons(tb: int, hwnd: int, buttons) -> int:
    return _thumb_call(tb, _THUMB_BAR_UPDATE, hwnd, buttons)


def set_thumbnail_tooltip(tb: int, hwnd: int, text: str) -> int:
    """The caption above the hover thumbnail. NULL puts the window title back.

    The raw HRESULT comes back for the same reason ThumbBarAddButtons' does:
    a caption that never appears is indistinguishable from one that was
    refused, unless the number is looked at."""
    vtbl = ctypes.cast(tb, ctypes.POINTER(ctypes.c_void_p))[0]
    fn = ctypes.cast(vtbl,
                     ctypes.POINTER(ctypes.c_void_p))[_SET_THUMBNAIL_TOOLTIP]
    proto = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p,
                               ctypes.c_void_p, wintypes.LPCWSTR)
    return proto(fn)(tb, ctypes.c_void_p(hwnd), text or None)


