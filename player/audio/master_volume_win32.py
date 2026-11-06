"""What Windows says about one output device — raw ctypes, read-only.

Two facts, both from the device's endpoint: the master slider of the taskbar
(the music in the ears is the app's fader TIMES it) and the FORM FACTOR the
driver reports — headphones, a headset, speakers, line-level (an audio
interface like a Maya), S/PDIF, HDMI. The form factor is what tells a headset
from an external sound card; the name alone cannot.
Same approach as player.audio.system_sounds_win32: Core Audio called through
its vtables. Importing it on a Mac raises.
"""

import ctypes
import sys

if sys.platform != "win32":   # pragma: no cover - guarded by the caller
    raise ImportError("player.audio.master_volume_win32 is Windows-only")

from shared.taskbar_win32 import GUID, method, release

_ole32 = ctypes.windll.ole32

_GET_DEFAULT_ENDPOINT = 4      # IMMDeviceEnumerator
_GET_DEVICE = 5
_ACTIVATE = 3                  # IMMDevice
_OPEN_PROPERTY_STORE = 4
_GET_MASTER_SCALAR = 9         # IAudioEndpointVolume
_GET_VALUE = 5                 # IPropertyStore

_E_RENDER = 0
_E_CONSOLE = 0
_CLSCTX_ALL = 0x17
_STGM_READ = 0
_VT_UI4 = 19

_CLSID_MM_DEVICE_ENUMERATOR = GUID(0xBCDE0395, 0xE52F, 0x467C,
                                    (0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E))
_IID_MM_DEVICE_ENUMERATOR = GUID(0xA95664D2, 0x9614, 0x4F35,
                                  (0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6))
_IID_ENDPOINT_VOLUME = GUID(0x5CDF2C82, 0x841E, 0x4546,
                             (0x97, 0x22, 0x0C, 0xF7, 0x40, 0x78, 0x22, 0x9A))


class _PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_ulong)]


# PKEY_AudioEndpoint_FormFactor
_KEY_FORM_FACTOR = _PROPERTYKEY(GUID(0x1DA5D803, 0xD492, 0x4EDD,
                                     (0x8C, 0x23, 0xE0, 0xC0, 0xFF, 0xEE, 0x7F, 0x0E)), 0)

_PTR = ctypes.POINTER(ctypes.c_void_p)


def _master(dev: int) -> float | None:
    ep = ctypes.c_void_p()
    method(dev, _ACTIVATE, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p, _PTR)(
        dev, ctypes.byref(_IID_ENDPOINT_VOLUME), _CLSCTX_ALL, None, ctypes.byref(ep))
    if not ep.value:
        return None
    level = ctypes.c_float()
    try:
        method(ep.value, _GET_MASTER_SCALAR, ctypes.POINTER(ctypes.c_float))(
            ep.value, ctypes.byref(level))
    finally:
        release(ep.value)
    return max(0.0, min(1.0, level.value))


def _form_factor(dev: int) -> int | None:
    store = ctypes.c_void_p()
    method(dev, _OPEN_PROPERTY_STORE, ctypes.c_ulong, _PTR)(
        dev, _STGM_READ, ctypes.byref(store))
    if not store.value:
        return None
    var = (ctypes.c_ubyte * 24)()   # PROPVARIANT: vt at 0, the value at 8
    try:
        method(store.value, _GET_VALUE, ctypes.POINTER(_PROPERTYKEY), ctypes.c_void_p)(
            store.value, ctypes.byref(_KEY_FORM_FACTOR), ctypes.addressof(var))
    finally:
        release(store.value)
    if ctypes.c_ushort.from_buffer(var).value != _VT_UI4:
        return None
    return ctypes.c_ulong.from_buffer(var, 8).value


def endpoint_info(endpoint_id: str = "") -> tuple[float | None, int | None]:
    """(master 0..1, form factor) of the device with this endpoint id, or of the
    default output when the id is empty or unknown. None for what Windows
    would not say."""
    enum = ctypes.c_void_p()
    hr = _ole32.CoCreateInstance(ctypes.byref(_CLSID_MM_DEVICE_ENUMERATOR), None,
                                 _CLSCTX_ALL, ctypes.byref(_IID_MM_DEVICE_ENUMERATOR),
                                 ctypes.byref(enum))
    if hr < 0 or not enum.value:
        return None, None
    dev = ctypes.c_void_p()
    try:
        try:
            if endpoint_id:
                method(enum.value, _GET_DEVICE, ctypes.c_wchar_p, _PTR)(
                    enum.value, endpoint_id, ctypes.byref(dev))
        except OSError:
            dev = ctypes.c_void_p()
        if not dev.value:
            method(enum.value, _GET_DEFAULT_ENDPOINT, ctypes.c_int, ctypes.c_int,
                   _PTR)(enum.value, _E_RENDER, _E_CONSOLE, ctypes.byref(dev))
        if not dev.value:
            return None, None
        try:
            try:
                master = _master(dev.value)
            except OSError:
                master = None
            try:
                form = _form_factor(dev.value)
            except OSError:
                form = None
            return master, form
        finally:
            release(dev.value)
    except OSError:
        return None, None
    finally:
        release(enum.value)
