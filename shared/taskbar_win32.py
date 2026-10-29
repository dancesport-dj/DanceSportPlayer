"""The Win32 half of the taskbar mini player — raw ctypes, no dependencies.

Qt6 dropped QtWinExtras, and this machine has no pywin32, no comtypes and no
winrt, so the thumbnail toolbar has to be driven by hand: an ITaskbarList3
built through CoCreateInstance and called through its vtable by index.

Nothing Qt lives here and nothing here decides anything — player.widgets.taskbar owns the
state, this module only carries it across to the shell. Importing it on a Mac
raises, so the caller checks sys.platform first; that is the whole reason it is
a separate file.
"""

import ctypes
import sys
from ctypes import wintypes

if sys.platform != "win32":   # pragma: no cover - guarded by the caller
    raise ImportError("shared.taskbar_win32 is Windows-only")

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

class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


_CLSID_TASKBAR_LIST = GUID(0x56FDF344, 0xFD6D, 0x11D0,
                            (0x95, 0x8A, 0x00, 0x60, 0x97, 0xC9, 0xA0, 0x90))
_IID_TASKBAR_LIST3 = GUID(0xEA1AFB91, 0x9E28, 0x4B86,
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


def method(ptr: int, slot: int, *argtypes):
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
        method(ptr.value, _HR_INIT)(ptr.value)
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


# ── 📌 Relaunch properties: what a taskbar pin of the window starts ───────────
# PKEY_AppUserModel_* (propkey.h), all under one format id. The relaunch keys
# count only on a window that carries the ID key as well.
_FMTID_APP_USER_MODEL = GUID(0x9F4C2855, 0x9F79, 0x4B39,
                              (0xA8, 0xD0, 0xE1, 0xD4, 0x2D, 0xE1, 0xD5, 0xF3))
PID_RELAUNCH_COMMAND = 2
PID_RELAUNCH_ICON = 3
PID_RELAUNCH_NAME = 4
PID_ID = 5

_IID_PROPERTY_STORE = GUID(0x886D8EEB, 0x8CF2, 0x4446,
                            (0x8D, 0x02, 0xCD, 0xBA, 0x1D, 0xBD, 0xCF, 0x99))
# IPropertyStore vtable slots, after IUnknown's three.
_PS_GET_VALUE = 5
_PS_SET_VALUE = 6
_PS_COMMIT = 7
_VT_LPWSTR = 31


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.DWORD)]


class _PROPVARIANT(ctypes.Structure):
    """Just the string arm of the union, padded to the full 16 bytes."""
    _fields_ = [("vt", wintypes.USHORT), ("r1", wintypes.WORD),
                ("r2", wintypes.WORD), ("r3", wintypes.WORD),
                ("pwszVal", ctypes.c_void_p), ("pad", ctypes.c_void_p)]


def _window_store(hwnd: int) -> int | None:
    ptr = ctypes.c_void_p()
    hr = ctypes.windll.shell32.SHGetPropertyStoreForWindow(
        ctypes.c_void_p(hwnd), ctypes.byref(_IID_PROPERTY_STORE), ctypes.byref(ptr))
    return ptr.value if hr >= 0 and ptr.value else None


def set_relaunch_properties(hwnd: int, app_id: str, command: str, icon: str,
                            name: str) -> bool:
    """Tell the shell how to start the app again from a pin of `hwnd`.

    Under an explicit AppUserModelID the shell pins neither the running exe
    nor its icon: without a shortcut of the same ID, or these keys, the pin
    comes out as a white box. The ID goes on last — it is what makes the
    shell read the other three."""
    store = _window_store(hwnd)
    if store is None:
        return False
    set_value = method(store, _PS_SET_VALUE, ctypes.POINTER(_PROPERTYKEY),
                        ctypes.POINTER(_PROPVARIANT))
    try:
        for pid, text in ((PID_RELAUNCH_COMMAND, command), (PID_RELAUNCH_ICON, icon),
                          (PID_RELAUNCH_NAME, name), (PID_ID, app_id)):
            buf = ctypes.create_unicode_buffer(text)   # SetValue copies it
            value = _PROPVARIANT(vt=_VT_LPWSTR, pwszVal=ctypes.addressof(buf))
            set_value(store, _PROPERTYKEY(_FMTID_APP_USER_MODEL, pid), value)
        method(store, _PS_COMMIT)(store)
    except OSError:   # a failed HRESULT
        return False
    finally:
        release(store)
    return True


def window_property(hwnd: int, pid: int) -> str | None:
    """One PKEY_AppUserModel_* string as the shell now holds it for `hwnd`."""
    store = _window_store(hwnd)
    if store is None:
        return None
    value = _PROPVARIANT()
    try:
        method(store, _PS_GET_VALUE, ctypes.POINTER(_PROPERTYKEY),
                ctypes.POINTER(_PROPVARIANT))(
            store, _PROPERTYKEY(_FMTID_APP_USER_MODEL, pid), value)
        if value.vt != _VT_LPWSTR:
            return None
        return ctypes.wstring_at(value.pwszVal)
    except OSError:
        return None
    finally:
        _ole32.PropVariantClear(ctypes.byref(value))
        release(store)


