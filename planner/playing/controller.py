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
DECK_COUNT = 8
WISH_COUNT = 4

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
    ("vol_up", "🔼  Music volume up"),
    ("vol_down", "🔽  Music volume down"),
    ("cart_volume", "🎛  Cartwall volume (fader or knob)"),
    ("cart_vol_up", "🔼  Cartwall volume up"),
    ("cart_vol_down", "🔽  Cartwall volume down"),
    ("cart_page_prev", "◀  Previous cartwall page"),
    ("cart_page_next", "▶  Next cartwall page"),
    ("tempo", "🎚  Tempo / pitch (fader or knob)"),
    ("tempo_up", "⏫  Tempo up"),
    ("tempo_down", "⏬  Tempo down"),
    ("tempo_reset", "🎯  Tempo back to ±0 %"),
    ("stop_pads", "⏹  Stop all pads"),
) + tuple((f"deck:{n}", f"🎯  Focus playlist {n}") for n in range(1, DECK_COUNT + 1)) \
  + tuple((f"wish:{n}", f"🎯  Focus wishlist {n}") for n in range(1, WISH_COUNT + 1)) \
  + (("lib", "📚  Focus the library"),
     ("browse", "🔄  Browse the list (endless knob)"),
     ("browse_up", "⬆  Browse up"),
     ("browse_down", "⬇  Browse down"),
     ("pick_play", "▶  Play the selected title"),
     ("pick_deck", "➕  Selected title to the playlist"),
     ("pick_wish", "⭐  Selected title to the wishlist")) \
  + tuple((f"pad:{n}", f"🎛  Cartwall pad {n}") for n in range(1, PAD_COUNT + 1))
ACTION_IDS = tuple(a for a, _label in ACTIONS)
CONTINUOUS = frozenset({"volume", "cart_volume", "tempo", "browse"})

# ⌨ The keyboard's share of the same actions, the desk keys (setting
# "desk_keys": action → its keys in Qt's portable text, [] for none; a single
# string from before an action could have several still reads). A fader is
# no key, and the pads have their own keys on the 🎛 wall. The 🎯 focus keys
# are Alt+1…8 and Alt+Q W E R, the row below: Ctrl+1…9 fire the wall's pads,
# and Shift would turn a digit into a symbol on most layouts.
KEY_ACTIONS = tuple(a for a in ACTION_IDS
                    if a not in CONTINUOUS and not a.startswith("pad:"))
KEY_DEFAULTS = {"toggle": "Ctrl+Shift+P", "next": "Ctrl+Shift+Right",
                "prev": "Ctrl+Shift+Left", "fade": "Ctrl+Shift+F",
                "hold": "Ctrl+Shift+H", "duck": "Ctrl+Shift+D",
                "announce": "Ctrl+Shift+A", "vol_up": "Ctrl+Shift+Up",
                "vol_down": "Ctrl+Shift+Down", "cart_vol_up": "Ctrl+Alt+Up",
                "cart_vol_down": "Ctrl+Alt+Down", "cart_page_prev": "Ctrl+Alt+Left",
                "cart_page_next": "Ctrl+Alt+Right", "tempo_up": "Ctrl+Shift+PgUp",
                "tempo_down": "Ctrl+Shift+PgDown", "tempo_reset": "Ctrl+Shift+Home",
                "stop_pads": "Ctrl+Shift+X",
                **{f"deck:{n}": f"Alt+{n}" for n in range(1, DECK_COUNT + 1)},
                **{f"wish:{n}": f"Alt+{k}" for n, k in enumerate("QWER", 1)},
                "lib": "Alt+L", "browse_up": "Alt+Up", "browse_down": "Alt+Down",
                "pick_play": "Alt+P", "pick_deck": "Alt+A", "pick_wish": "Alt+D"}
VOLUME_STEP = 0.05

# The keys the app answers to already, in the F1 cheat sheet's words. A desk
# key on one of them takes it from the app, or makes Qt drop both.
_CART_KEYS = {f"Ctrl+{n}": "🎛  Cartwall" for n in range(1, 10)}
RESERVED_KEYS = {
    "Space": "Play / stop the selected song",
    "Return": "Play / stop the selected song — in Playing mode also in the "
              "list playing, where Space pauses the player",
    "Enter": "Play / stop the selected song — in Playing mode also in the "
             "list playing, where Space pauses the player",
    "Ctrl+Left": "Seek 30 s back / forward while playing",
    "Ctrl+Right": "Seek 30 s back / forward while playing",
    "Ctrl+R": "Re-roll (regenerate) the selected song",
    "Ctrl+N": "Re-roll (regenerate) the selected song",
    "Ctrl+S": "Save the focused playlist / wishlist as M3U",
    "Ctrl+Shift+S": "Save the whole session state (decks, wishlists, layout)",
    "Ctrl+Z": "Undo / redo (also Ctrl + Shift + Z)",
    "Ctrl+Y": "Undo / redo (also Ctrl + Shift + Z)",
    "Ctrl+Shift+Z": "Undo / redo (also Ctrl + Shift + Z)",
    "Ctrl+X": "Close the active dialog or the preview mini player",
    "Ctrl+W": "Close the active dialog or the preview mini player",
    "Del": "Remove the selected rows (wishlist) / empty the selected heat "
           "slots (deck)",
    "Ctrl+Shift+Del": "Clear the focused playlist / wishlist (confirmed), "
                      "wherever the cursor is",
    "Ctrl+F": "Find a title in the focused list (repeat to step to the next "
              "match)",
    "Alt+S": "Warm-up list: swap the two selected titles of one dance",
    "F1": "This cheat sheet",
    "F11": "Fullscreen on / off — with date and time in the status bar",
    "F12": "Open ⚙ Settings",
    "Ctrl+Alt+S": "Open ⚙ Settings",
    "Esc": "Stop every pad (same as ⏹ Stop all)",
    **_CART_KEYS,
}
_KEY_GLYPHS = {"Left": "←", "Right": "→", "Up": "↑", "Down": "↓"}

# Korg nanoKONTROL2 in its factory CC mode (global MIDI channel 1), laid out
# as played at the desk. The transport row drives the player, fader 1 is the
# music volume, fader 2 the cartwall's, the knob above fader 1 the tempo and S1 puts the tempo back to
# ±0 % (the knobs have no push switch). TRACK ▶ focuses the library, the
# MARKER buttons browse the list in focus (its knobs have end stops, so none
# is the browse knob) and S2-S4 play the selected title or send it to the
# playlist / wishlist. The cartwall pads sit on the S/M/R buttons of strips
# 5-8 and on M1-M4; pads 13 and 14 stay free.
_NANO_CCS = {"toggle": 41, "fade": 42, "prev": 43, "next": 44,
             "hold": 45, "announce": 46, "duck": 58, "stop_pads": 60,
             "volume": 0, "cart_volume": 1, "tempo": 16, "tempo_reset": 32,
             "lib": 59, "browse_up": 61, "browse_down": 62,    # TRACK ▶, MARKER ◀ ▶
             "pick_play": 33, "pick_deck": 34, "pick_wish": 35,  # S2 S3 S4
             "pad:1": 36, "pad:2": 52, "pad:3": 68,       # S5 M5 R5
             "pad:4": 37, "pad:5": 53, "pad:6": 69,       # S6 M6 R6
             "pad:7": 38, "pad:8": 39,                    # S7 S8
             "pad:9": 48, "pad:10": 49, "pad:11": 50, "pad:12": 51,  # M1-M4
             "pad:15": 54, "pad:16": 55}                  # M7 M8
PRESETS = {
    "Korg nanoKONTROL2": {
        "device": "nanoKONTROL2",
        "bindings": {action: f"cc:0:{cc}" for action, cc in _NANO_CCS.items()},
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


def knob_offset(value: float) -> float:
    """A knob's 0…1 as −1…+1 around its middle, for the tempo fader. A 7-bit
    knob has no middle step (63 and 64 straddle it), so both read as 0:
    turned back to the middle, the tempo is ±0 %, not ±0.1 %."""
    offset = value * 2 - 1
    return 0.0 if abs(offset) <= 1.5 / 127 else offset


def encoder_steps(value: float) -> int:
    """An endless knob's reading as steps, + clockwise. Such a knob sends how
    far it was turned, not where it stands, in one of two codes: 1, 2, …
    right and 127, 126, … left, or 65, 66, … right and 63, 62, … left. A
    reading is rarely more than a few steps, so where it lies tells which."""
    v = round(value * 127)
    if v < 32:
        return v
    if v > 96:
        return v - 128
    return v - 64


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
    the volume, a single HID bit only for a button; a MIDI key only for a
    button, a pitch bend only for the volume; the browse knob only a MIDI
    CC. A MIDI CC fits either, and `learn_takes` tells which it is by how it
    moves."""
    if control.startswith("note:"):
        return action not in CONTINUOUS
    if action == "browse":
        return control.startswith("cc:")   # encoder_steps reads MIDI's 7 bits
    if control.startswith("pb:"):
        return action in CONTINUOUS
    if not control.startswith("hid:"):
        return True
    is_bit = control.count(":") == 3
    return is_bit != (action in CONTINUOUS)


def learn_takes(action: str, control: str, value: float, swept: set) -> bool:
    """Whether a reading while Learn waits teaches `control` to `action`.
    A CC is a button or a knob, and only its values tell: a button jumps
    between 0 and 127, a knob or fader passes the steps between. `swept`
    collects the CCs seen between; this reading is added to it."""
    if not learnable(action, control):
        return False
    if control.startswith("cc:") and 0.0 < value < 1.0:
        swept.add(control)
    if action in CONTINUOUS:
        return not control.startswith("cc:") or control in swept
    if value < 0.5:
        return False    # a release, or a fader at rest: wait for the press
    return not control.startswith("cc:") or (value == 1.0
                                             and control not in swept)


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


def desk_keys(saved) -> dict:
    """{action: [keys]} for every KEY_ACTION: the saved choice over the
    default, "" or [] unbinding one. A key on two actions stays with the one
    listed first — two shortcuts on one key are ambiguous to Qt, and then
    neither fires."""
    saved = saved if isinstance(saved, dict) else {}
    out, taken = {}, set()
    for action in KEY_ACTIONS:
        default = [KEY_DEFAULTS.get(action, "")]
        raw = saved.get(action, default)
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, list) or not all(isinstance(k, str) for k in raw):
            raw = default
        out[action] = []
        for key in raw:
            if key and key not in taken:
                out[action].append(key)
                taken.add(key)
    return out


def key_clashes(keys: dict, taken: dict | None = None) -> dict:
    """{(action, n): what else answers to its n-th key}: what `taken`
    ({key: label}, the 🎛 wall's keys) says — it names the pad or slot,
    where the app only knows "Cartwall" —, the cheat sheet's words for a key
    of the app's own, or the label of the action that has it first, which
    keeps it (see desk_keys). `n` counts the "" of an empty field too."""
    labels = dict(ACTIONS)
    taken = taken or {}
    out: dict[tuple[str, int], str] = {}
    owner: dict[str, str] = {}
    for action in KEY_ACTIONS:
        for n, key in enumerate(keys.get(action) or []):
            if not key:
                continue
            if key in taken:
                out[(action, n)] = taken[key]
            elif key in RESERVED_KEYS:
                out[(action, n)] = RESERVED_KEYS[key]
            elif key in owner:
                out[(action, n)] = labels[owner[key]]
            else:
                owner[key] = action
    return out


def keys_outside_wall(desk: dict) -> dict:
    """{key: what answers to it} that a 🎛 wall key must not take: the app's
    own keys but the wall's slot keys, and the desk keys. Two shortcuts on
    one key are ambiguous to Qt, so neither would fire."""
    out = {k: v for k, v in RESERVED_KEYS.items() if k not in _CART_KEYS}
    labels = dict(ACTIONS)
    for action in KEY_ACTIONS:
        for key in desk.get(action) or []:
            if key and key not in out:
                out[key] = labels[action]
    return out


def key_text(key: str) -> str:
    """A key as the F1 cheat sheet spells it: "Ctrl + Shift + →"."""
    parts = key[:-2].split("+") + ["+"] if key.endswith("++") else key.split("+")
    return " + ".join(_KEY_GLYPHS.get(p, p) for p in parts)


class ControllerMap:
    """Turns a stream of (control, value) into the actions to run."""

    def __init__(self, bindings: dict):
        self._by_control = {c: a for a, c in clean_bindings(bindings).items()}
        self._last: dict[str, float] = {}

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
