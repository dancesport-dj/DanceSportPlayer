"""🎛 Hardware controller profiles (no Qt): which knob or button does what.

A profile maps ACTIONS to CONTROLS. An action is one of the things the 📱
phone remote can already do (play/pause, next, fade, a cartwall pad, …) plus
the music volume; a control is one physical element, named the way it
reaches the app:

    cc:<ch>:<n>        MIDI control change n on channel ch (0-based)
    note:<ch>:<n>      MIDI note n
    pb:<ch>            MIDI pitch bend (some faders send that)
    hid:<r>:<i>:<bit>  HID report r, byte i, one bit — a button
    hid:<r>:<i>        HID report r, byte i as a value — a knob or fader

Every control arrives as a value 0…1. A button action fires once on the
press (the value crossing ½ upwards), so a button that also sends its
release, or a fader swept past the middle, does not fire twice; the volume
action takes the value itself.

Profiles are JSON files Marcel can keep per controller; the ones that ship
are in PRESETS.
"""
import json
from pathlib import Path

PROFILE_VERSION = 1
PAD_COUNT = 16

# (id, label) in the order the 🎛 Controller dialog lists them. The ids are
# the phone remote's commands wherever one exists, so both drive the desk
# through the same switch.
ACTIONS = (
    ("toggle", "⏯  Play / pause"),
    ("next", "⏭  Next title"),
    ("prev", "⏮  Previous title"),
    ("fade", "🔉↓  Fade out now"),
    ("hold", "🛑  Fade out and hold"),
    ("duck", "🔉  Duck the music on / off"),
    ("announce", "🔈  Announce the next dance on / off"),
    ("volume", "🔊  Music volume (fader or knob)"),
    ("stop_pads", "⏹  Stop all pads"),
) + tuple((f"pad:{n}", f"🎛  Cartwall pad {n}") for n in range(1, PAD_COUNT + 1))
ACTION_IDS = tuple(a for a, _label in ACTIONS)
CONTINUOUS = frozenset({"volume"})

# Korg nanoKONTROL2 in its factory CC mode (global MIDI channel 1). The
# transport row drives the player, the S and M buttons are the first sixteen
# cartwall pads of the page on screen and fader 1 is the music volume.
_NANO_TRANSPORT = {"toggle": 41, "fade": 42, "prev": 43, "next": 44,
                   "hold": 45, "announce": 46, "duck": 58,
                   "stop_pads": 60, "volume": 0}
PRESETS = {
    "Korg nanoKONTROL2": {
        "device": "nanoKONTROL2",
        "bindings": {
            **{action: f"cc:0:{cc}" for action, cc in _NANO_TRANSPORT.items()},
            **{f"pad:{n}": f"cc:0:{31 + n}" for n in range(1, 9)},      # S1-S8
            **{f"pad:{n}": f"cc:0:{39 + n}" for n in range(9, 17)},     # M1-M8
        },
    },
}


def midi_control(status: int, data1: int, data2: int):
    """A MIDI short message → (control, value 0…1), or None for anything
    that is not a key, a controller or a bend (clock, aftertouch, …)."""
    kind, ch = status & 0xF0, status & 0x0F
    if kind == 0x90:
        return f"note:{ch}:{data1}", data2 / 127
    if kind == 0x80:
        return f"note:{ch}:{data1}", 0.0
    if kind == 0xB0:
        return f"cc:{ch}:{data1}", data2 / 127
    if kind == 0xE0:
        return f"pb:{ch}", ((data2 << 7) | data1) / 16383
    return None


def hid_controls(prev: bytes, cur: bytes) -> list:
    """What changed between two HID input reports of the same id, as
    (control, value) pairs. Each changed byte yields a value control and
    one bit control per flipped bit: which of them a profile binds decides
    whether that byte is read as buttons or as a knob — the report itself
    cannot say."""
    if not cur:
        return []
    report = cur[0]
    out = []
    for i in range(1, len(cur)):
        old = prev[i] if i < len(prev) else 0
        new = cur[i]
        if old == new:
            continue
        out.append((f"hid:{report}:{i}", new / 255))
        for bit in range(8):
            if (old ^ new) >> bit & 1:
                out.append((f"hid:{report}:{i}:{bit}", float(new >> bit & 1)))
    return out


def learnable(action: str, control: str) -> bool:
    """Whether a control may be learned for an action: a HID byte only for
    the volume, a single HID bit only for a button. MIDI fits either."""
    if not control.startswith("hid:"):
        return True
    is_bit = control.count(":") == 3
    return is_bit != (action in CONTINUOUS)


def control_label(control: str) -> str:
    """A control as the dialog shows it."""
    parts = control.split(":")
    try:
        if parts[0] == "cc":
            return f"CC {parts[2]} · ch {int(parts[1]) + 1}"
        if parts[0] == "note":
            return f"Note {parts[2]} · ch {int(parts[1]) + 1}"
        if parts[0] == "pb":
            return f"Pitch bend · ch {int(parts[1]) + 1}"
        if parts[0] == "hid" and len(parts) == 4:
            return f"HID {parts[1]} · byte {parts[2]} · bit {parts[3]}"
        if parts[0] == "hid" and len(parts) == 3:
            return f"HID {parts[1]} · byte {parts[2]}"
    except (IndexError, ValueError):
        pass
    return control


def clean_bindings(raw) -> dict:
    """Bindings from a file, made safe: known actions only, string controls,
    and no control bound twice (the first action listed keeps it)."""
    if not isinstance(raw, dict):
        return {}
    out, taken = {}, set()
    for action in ACTION_IDS:
        control = raw.get(action)
        if isinstance(control, str) and control and control not in taken:
            out[action] = control
            taken.add(control)
    return out


def bind(bindings: dict, action: str, control: str) -> dict:
    """A copy with `control` on `action` — taken off whatever action had it."""
    out = {a: c for a, c in bindings.items() if c != control}
    out[action] = control
    return out


def load_profile(path) -> dict:
    """A profile file → {"name", "device", "bindings"}. Raises OSError or
    ValueError for a file that is not one."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or not isinstance(doc.get("bindings"), dict):
        raise ValueError("not a controller profile")
    return {"name": str(doc.get("name") or Path(path).stem),
            "device": str(doc.get("device") or ""),
            "bindings": clean_bindings(doc["bindings"])}


def save_profile(path, name: str, device: str, bindings: dict) -> None:
    doc = {"version": PROFILE_VERSION, "name": name, "device": device,
           "bindings": clean_bindings(bindings)}
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")


class ControllerMap:
    """Turns a stream of (control, value) into the actions to run."""

    def __init__(self, bindings: dict):
        self._by_control = {c: a for a, c in clean_bindings(bindings).items()}
        self._last = {}

    def feed(self, control: str, value: float) -> list:
        """(action, value) pairs to run for one control reading — at most one."""
        action = self._by_control.get(control)
        prev = self._last.get(control, 0.0)
        self._last[control] = value
        if action is None:
            return []
        if action in CONTINUOUS:
            return [(action, value)]
        if value >= 0.5 > prev:
            return [(action, value)]
        return []
