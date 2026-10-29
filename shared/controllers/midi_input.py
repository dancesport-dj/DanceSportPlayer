"""🎛 MIDI input from a hardware controller, on every platform the app runs on.

One interface, three backends, each through raw ctypes against what the
system already ships — python-rtmidi has no wheel for this Python and would
need a C++ toolchain to build:

    Windows  winmm            shared/controllers/midi_winmm.py
    macOS    CoreMIDI         shared/controllers/midi_coremidi.py
    Linux    ALSA sequencer   shared/controllers/midi_alsa.py (libasound.so.2)

`list_inputs()` names the inputs plugged in now; `MidiInput(name,
on_message)` opens one and calls `on_message(status, data1, data2)` for every
channel message, on the backend's own thread — the caller moves it onto the
GUI thread (a Qt signal does). `close()` stops it. Where the backend's
library is missing there are simply no inputs.

Nothing Qt lives here.
"""

import sys

__all__ = ["MidiInput", "MidiStreamParser", "list_inputs", "unique_names"]

# Data bytes after a channel status: note off/on, poly pressure, control
# change, program change, channel pressure, pitch bend.
_DATA_BYTES = {0x80: 2, 0x90: 2, 0xA0: 2, 0xB0: 2, 0xC0: 1, 0xD0: 1, 0xE0: 2}

class MidiStreamParser:
    """Raw MIDI bytes → (status, data1, data2) channel messages.

    For a backend that hands over bytes rather than messages (CoreMIDI). Keeps
    running status across calls, skips real-time bytes wherever they fall, and
    drops system exclusive and system common messages — no control lives
    there."""

    def __init__(self):
        self._status = 0        # running status; 0 = none
        self._data = []
        self._in_sysex = False

    def feed(self, data: bytes) -> list[tuple[int, int, int]]:
        out = []
        for byte in data:
            if byte >= 0xF8:            # real time: clock, start, sensing, …
                continue
            if byte & 0x80:
                self._in_sysex = byte == 0xF0
                # A system common message cancels running status.
                self._status = byte if byte < 0xF0 else 0
                self._data = []
                continue
            if self._in_sysex or not self._status:
                continue
            self._data.append(byte)
            if len(self._data) == _DATA_BYTES[self._status & 0xF0]:
                d1, d2 = (self._data + [0])[:2]
                out.append((self._status, d1, d2))
                self._data = []
        return out


def unique_names(names: list[str]) -> list[str]:
    """The same name twice (two identical controllers) gets " #2", " #3", …
    so each still opens by name."""
    out, seen = [], {}
    for name in names:
        seen[name] = seen.get(name, 0) + 1
        out.append(name if seen[name] == 1 else f"{name} #{seen[name]}")
    return out


if sys.platform == "win32":
    from shared.controllers.midi_winmm import MidiInput, list_inputs
elif sys.platform == "darwin":   # pragma: no cover - macOS only
    from shared.controllers.midi_coremidi import MidiInput, list_inputs
elif sys.platform.startswith("linux"):   # pragma: no cover - Linux only
    from shared.controllers.midi_alsa import MidiInput, list_inputs
else:   # pragma: no cover
    def list_inputs() -> list[str]:
        return []

    class _NoMidiInput:
        name = ""

        def __init__(self, name: str, on_message):
            raise OSError(f"no MIDI input on {sys.platform}")

        def close(self) -> None:
            pass

    MidiInput = _NoMidiInput
