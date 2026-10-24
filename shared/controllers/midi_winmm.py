"""🎛 MIDI input on Windows — winmm through raw ctypes.

winmm ships with every Windows and reads any class-compliant USB MIDI device
(Korg nanoKONTROL2, a Traktor controller in MIDI mode, …), so the few calls
needed are made by hand, in the same spirit as taskbar_win32. Use it through
shared.controllers.midi_input, which picks the backend for the platform.

winmm delivers each message on a thread of its own and `MidiInput` hands it
to the callback it was given, straight from that thread.
"""
from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger("dancesport.midi")

_CALLBACK_FUNCTION = 0x30000
_MIM_DATA = 0x3C3
_MAXPNAMELEN = 32

if sys.platform == "win32":
    from ctypes import wintypes

    _winmm = ctypes.windll.winmm

    class _MidiInCaps(ctypes.Structure):
        _fields_ = [("wMid", wintypes.WORD), ("wPid", wintypes.WORD),
                    ("vDriverVersion", wintypes.UINT),
                    ("szPname", wintypes.WCHAR * _MAXPNAMELEN),
                    ("dwSupport", wintypes.DWORD)]

    _MidiInProc = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.UINT,
                                     ctypes.c_size_t, ctypes.c_size_t,
                                     ctypes.c_size_t)
    _winmm.midiInGetNumDevs.restype = wintypes.UINT
    _winmm.midiInGetDevCapsW.argtypes = [ctypes.c_size_t,
                                         ctypes.POINTER(_MidiInCaps),
                                         wintypes.UINT]
    _winmm.midiInOpen.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.UINT,
                                  ctypes.c_size_t, ctypes.c_size_t,
                                  wintypes.DWORD]
    for _name in ("midiInStart", "midiInStop", "midiInReset", "midiInClose"):
        getattr(_winmm, _name).argtypes = [wintypes.HANDLE]
else:   # pragma: no cover - no winmm off Windows
    _winmm = None


def list_inputs() -> list[str]:  # slop-mop noqa: ambiguity-mine - the MIDI backend interface, one module per OS
    """The names of the MIDI inputs plugged in now, in winmm's order (the
    index is what `MidiInput` opens). Two identical units are told apart by
    `unique_names`, as on CoreMIDI and ALSA."""
    # Here, not at the top: midi_input imports this module while it loads.
    from shared.controllers.midi_input import unique_names
    if _winmm is None:
        return []
    names = []
    for idx in range(_winmm.midiInGetNumDevs()):
        caps = _MidiInCaps()
        if _winmm.midiInGetDevCapsW(idx, ctypes.byref(caps),
                                    ctypes.sizeof(caps)) == 0:
            names.append(caps.szPname)
        else:
            names.append("")
    return unique_names(names)


def unpack(packed: int) -> tuple[int, int, int]:
    """winmm's MIM_DATA word → (status, data1, data2)."""
    return packed & 0xFF, (packed >> 8) & 0x7F, (packed >> 16) & 0x7F


class MidiInput:
    """One open MIDI input. `on_message(status, data1, data2)` runs on
    winmm's thread for every short message; `close()` stops it."""

    def __init__(self, name: str, on_message):
        if _winmm is None:
            raise OSError("MIDI input needs Windows")
        names = list_inputs()
        if name not in names:
            raise OSError(f"MIDI input not found: {name}")
        self.name = name
        self._on_message = on_message

        def proc(_handle, msg, _instance, param1, _param2):
            if msg == _MIM_DATA:
                try:
                    self._on_message(*unpack(param1))
                except Exception:   # a raise here would unwind into winmm
                    log.exception("🎛 MIDI message handler failed")

        # Kept on the instance: winmm calls it until close(), and a collected
        # ctypes callback is a crash, not an exception.
        self._proc = _MidiInProc(proc)
        handle = wintypes.HANDLE()
        err = _winmm.midiInOpen(ctypes.byref(handle), names.index(name),
                                ctypes.cast(self._proc, ctypes.c_void_p).value,
                                0, _CALLBACK_FUNCTION)
        if err:
            raise OSError(f"midiInOpen failed ({err}) for {name} — "
                          "another program may hold it")
        self._handle = handle
        _winmm.midiInStart(handle)

    def close(self) -> None:
        handle, self._handle = getattr(self, "_handle", None), None
        if handle and _winmm is not None:
            _winmm.midiInStop(handle)
            _winmm.midiInReset(handle)
            _winmm.midiInClose(handle)
