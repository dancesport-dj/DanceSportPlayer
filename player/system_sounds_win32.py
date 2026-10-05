"""The Win32 half of 🔕 keeping Windows' own sounds off the PA — raw ctypes.

Windows plays every one of its sounds — the error ding, the notification chime,
a USB stick plugged in, and a QMessageBox of our own — through ONE audio session
per output device, the "System Sounds" slider of the volume mixer. Muting that
session silences all of them on that card while the music, which is a session
of its own, plays on untouched.

Same approach as player.taskbar_win32: no comtypes, no pycaw, so the Core Audio
interfaces are called through their vtables by index. Nothing here decides
anything — player.system_sounds owns the when. Importing it on a Mac raises.
"""
from __future__ import annotations

import ctypes
import sys

if sys.platform != "win32":   # pragma: no cover - guarded by the caller
    raise ImportError("player.system_sounds_win32 is Windows-only")

from player.taskbar_win32 import _GUID, _method, release   # noqa: E402

_ole32 = ctypes.windll.ole32

# Vtable slots, fixed by mmdeviceapi.h / audiopolicy.h / audioclient.h.
_QUERY_INTERFACE = 0
_ENUM_AUDIO_ENDPOINTS = 3      # IMMDeviceEnumerator
_COLLECTION_COUNT = 3          # IMMDeviceCollection
_COLLECTION_ITEM = 4
_ACTIVATE = 3                  # IMMDevice
_GET_ID = 5
_GET_SESSION_ENUMERATOR = 5    # IAudioSessionManager2
_SESSION_COUNT = 3             # IAudioSessionEnumerator
_GET_SESSION = 4
_IS_SYSTEM_SOUNDS = 15         # IAudioSessionControl2
_SET_MUTE = 5                  # ISimpleAudioVolume
_GET_MUTE = 6

_E_RENDER = 0
_DEVICE_STATE_ACTIVE = 1
_CLSCTX_ALL = 0x17
_S_OK = 0

_CLSID_MM_DEVICE_ENUMERATOR = _GUID(0xBCDE0395, 0xE52F, 0x467C,
                                    (0x8E, 0x3D, 0xC4, 0x57, 0x92, 0x91, 0x69, 0x2E))
_IID_MM_DEVICE_ENUMERATOR = _GUID(0xA95664D2, 0x9614, 0x4F35,
                                  (0xA7, 0x46, 0xDE, 0x8D, 0xB6, 0x36, 0x17, 0xE6))
_IID_AUDIO_SESSION_MANAGER2 = _GUID(0x77AA99A0, 0x1BD6, 0x484F,
                                    (0x8B, 0xC7, 0x2C, 0x65, 0x4C, 0x9A, 0x9B, 0x6F))
_IID_AUDIO_SESSION_CONTROL2 = _GUID(0xBFB7FF88, 0x7239, 0x4FC9,
                                    (0x8F, 0xA2, 0x07, 0xC9, 0x50, 0xBE, 0x9C, 0x6D))
_IID_SIMPLE_AUDIO_VOLUME = _GUID(0x87CE5498, 0x68D6, 0x44E5,
                                 (0x92, 0x15, 0x6D, 0xA4, 0x7E, 0xF8, 0x83, 0xD8))

_PTR = ctypes.POINTER(ctypes.c_void_p)


def _query(ptr: int, iid: _GUID) -> int | None:
    out = ctypes.c_void_p()
    try:
        _method(ptr, _QUERY_INTERFACE, ctypes.c_void_p, _PTR)(
            ptr, ctypes.byref(iid), ctypes.byref(out))
    except OSError:
        return None
    return out.value


def _system_sounds_of(device: int) -> int | None:
    """The ISimpleAudioVolume of one device's System Sounds session."""
    mgr = ctypes.c_void_p()
    _method(device, _ACTIVATE, ctypes.c_void_p, ctypes.c_ulong, ctypes.c_void_p,
            _PTR)(device, ctypes.byref(_IID_AUDIO_SESSION_MANAGER2),
                  _CLSCTX_ALL, None, ctypes.byref(mgr))
    sessions = ctypes.c_void_p()
    try:
        _method(mgr.value, _GET_SESSION_ENUMERATOR, _PTR)(
            mgr.value, ctypes.byref(sessions))
    finally:
        release(mgr.value)
    found = None
    try:
        count = ctypes.c_int()
        _method(sessions.value, _SESSION_COUNT, ctypes.POINTER(ctypes.c_int))(
            sessions.value, ctypes.byref(count))
        for i in range(count.value):
            ctl = ctypes.c_void_p()
            _method(sessions.value, _GET_SESSION, ctypes.c_int, _PTR)(
                sessions.value, i, ctypes.byref(ctl))
            ctl2 = _query(ctl.value, _IID_AUDIO_SESSION_CONTROL2)
            try:
                if ctl2 and _method(ctl2, _IS_SYSTEM_SOUNDS)(ctl2) == _S_OK:
                    found = _query(ctl.value, _IID_SIMPLE_AUDIO_VOLUME)
            finally:
                if ctl2:
                    release(ctl2)
                release(ctl.value)
            if found:
                break
    finally:
        release(sessions.value)
    return found


def _device_id(device: int) -> str:
    """The endpoint id — stable across unplugging and plugging back in."""
    out = ctypes.c_wchar_p()
    _method(device, _GET_ID, ctypes.POINTER(ctypes.c_wchar_p))(
        device, ctypes.byref(out))
    try:
        return out.value or ""
    finally:
        _ole32.CoTaskMemFree(out)


def system_sound_volumes() -> list[tuple[str, int]]:
    """(endpoint id, ISimpleAudioVolume) per active output device — all of
    them, not just the default: the operator can switch the default
    mid-evening and the app's music follows it. The caller releases every
    pointer it gets."""
    enum = ctypes.c_void_p()
    hr = _ole32.CoCreateInstance(ctypes.byref(_CLSID_MM_DEVICE_ENUMERATOR), None,
                                 _CLSCTX_ALL,
                                 ctypes.byref(_IID_MM_DEVICE_ENUMERATOR),
                                 ctypes.byref(enum))
    if hr < 0 or not enum.value:
        return []
    volumes: list[tuple[str, int]] = []
    try:
        coll = ctypes.c_void_p()
        _method(enum.value, _ENUM_AUDIO_ENDPOINTS, ctypes.c_int, ctypes.c_ulong,
                _PTR)(enum.value, _E_RENDER, _DEVICE_STATE_ACTIVE,
                      ctypes.byref(coll))
        try:
            count = ctypes.c_uint()
            _method(coll.value, _COLLECTION_COUNT, ctypes.POINTER(ctypes.c_uint))(
                coll.value, ctypes.byref(count))
            for i in range(count.value):
                dev = ctypes.c_void_p()
                _method(coll.value, _COLLECTION_ITEM, ctypes.c_uint, _PTR)(
                    coll.value, i, ctypes.byref(dev))
                vol = None
                try:
                    vol = _system_sounds_of(dev.value)
                    if vol:
                        volumes.append((_device_id(dev.value), vol))
                except OSError:   # a device that refuses — skip it, not all
                    if vol:
                        release(vol)
                finally:
                    release(dev.value)
        finally:
            release(coll.value)
    finally:
        release(enum.value)
    return volumes


def get_mute(vol: int) -> bool:
    muted = ctypes.c_int()
    _method(vol, _GET_MUTE, ctypes.POINTER(ctypes.c_int))(vol, ctypes.byref(muted))
    return bool(muted.value)


def set_mute(vol: int, on: bool) -> None:
    _method(vol, _SET_MUTE, ctypes.c_int, ctypes.c_void_p)(vol, int(on), None)
