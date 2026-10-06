"""🎨 Looks of your own: made in ⚙ Settings › Look, kept in looks.json.

A look of your own is a built-in one copied and re-coloured: every colour
token, the corner radius, the button, tab and focus style and the font can
change, and it keeps the family of the look it came from (shared/looks.py,
`Look.family`), so a copy of Console still draws faders. Whether it is dark is
read off its window colour rather than asked for, so it can never disagree
with what the look shows.

The file holds the looks of this machine; one look travels as its own .json
(Export / Import). Both are checked field by field when read: a look that
does not hold together is left out with a warning naming the field, and the
app carries on with the others.
"""
import dataclasses
import json
import logging
import re
import unicodedata
from pathlib import Path

from planner.store import JsonStore
from shared import looks, theme

log = logging.getLogger("dancesport.looks")

STORE = JsonStore("looks.json", note="using the built-in looks only")
VERSION = 1
GROUP = "user"
# What an exported file says it is, so an import can tell it from any other JSON.
FILE_MARK = "danceplaylist_look"
KEY_PREFIX = "own_"

COLOR_TOKENS = tuple(f.name for f in dataclasses.fields(looks.Tokens)
                     if f.name != "radius")
# Set, these turn a face into a gradient (the desk keys); empty is flat.
OPTIONAL_COLORS = ("surface_top", "header_top")
RADIUS_MAX = 20
_HEX = re.compile(r"#[0-9a-fA-F]{6}")


def is_dark(window: str) -> bool:
    """A window colour closer to black than to white makes a dark look."""
    return theme.contrast_ratio(window, "#000000") < theme.contrast_ratio(window, "#ffffff")


def to_dict(look: looks.Look) -> dict:
    return {"key": look.key, "name": look.caption, "family": looks.family(look),
            "buttons": look.buttons, "tabs": look.tabs, "focus": look.focus,
            "fonts": list(look.fonts), "tokens": dataclasses.asdict(look.tokens)}


def from_dict(data: dict) -> looks.Look:
    """The look a dict describes. ValueError, naming the field, when it does not
    describe one."""
    if not isinstance(data, dict):
        raise ValueError("not a look")
    key = str(data.get("key") or "")
    if not key.startswith(KEY_PREFIX) or key != slug(key):
        raise ValueError(f"key: {key!r}")
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValueError("name")
    family = data.get("family")
    if family not in {g for g, _label in looks.GROUPS}:
        raise ValueError(f"family: {family!r}")
    for field, allowed in (("buttons", looks.BUTTON_STYLES),
                           ("tabs", looks.TAB_STYLES),
                           ("focus", looks.FOCUS_STYLES)):
        if data.get(field) not in allowed:
            raise ValueError(f"{field}: {data.get(field)!r}")
    fonts = data.get("fonts")
    if (not isinstance(fonts, list) or not fonts
            or not all(isinstance(f, str) and f.strip() for f in fonts)):
        raise ValueError("fonts")
    raw = data.get("tokens")
    if not isinstance(raw, dict):
        raise ValueError("tokens")
    tokens = {}
    for name_ in COLOR_TOKENS:
        value = raw.get(name_, "" if name_ in OPTIONAL_COLORS else None)
        if value == "" and name_ in OPTIONAL_COLORS:
            tokens[name_] = ""
        elif isinstance(value, str) and _HEX.fullmatch(value):
            tokens[name_] = value.lower()
        else:
            raise ValueError(f"tokens.{name_}: {value!r}")
    radius = raw.get("radius")
    if not isinstance(radius, int) or isinstance(radius, bool) \
            or not 0 <= radius <= RADIUS_MAX:
        raise ValueError(f"tokens.radius: {radius!r}")
    tokens["radius"] = radius
    return looks.Look(
        key, GROUP, name, "", is_dark(tokens["window"]), looks.Tokens(**tokens),
        tuple(f.strip() for f in fonts), data["buttons"], tabs=data["tabs"],
        focus=data["focus"], family=family)


def slug(text: str) -> str:
    """Lower-case ASCII letters, digits and underscores — a theme key."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", plain.lower()).strip("_")


def new_key(name: str) -> str:
    """A key for a new look of that name that no theme uses yet."""
    base = KEY_PREFIX + (slug(name) or "look")
    key, n = base, 2
    while theme.is_theme(key):
        key, n = f"{base}_{n}", n + 1
    return key


def copy_of(source: looks.Look, name: str) -> looks.Look:
    """A new look of your own, starting as `source` re-named."""
    return dataclasses.replace(
        source, key=new_key(name), group=GROUP, caption=name, blurb="",
        family=looks.family(source))


def mine() -> list[looks.Look]:
    """The looks of your own, in the order they were made."""
    return [look for look in looks.LOOKS.values() if look.group == GROUP]


# ── The file ────────────────────────────────────────────────────────────────

def load() -> list[looks.Look]:
    """Read looks.json into the registry, beside the built-in looks. Before the
    theme is applied at start-up, or a stored own look reads as unknown and
    the app falls back to light."""
    for look in mine():
        del looks.LOOKS[look.key]
    doc = STORE.read({})
    entries = doc.get("looks") if isinstance(doc, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        try:
            look = from_dict(entry)
        except ValueError as exc:
            log.warning("🎨 Own look left out\n"
                        "file: %s\n"
                        "error: %s", STORE.name, exc)
            continue
        if theme.is_theme(look.key):
            log.warning("🎨 Own look left out\n"
                        "file: %s\n"
                        "error: the key %s is taken", STORE.name, look.key)
            continue
        looks.LOOKS[look.key] = look
    return mine()


def _save() -> bool:
    return STORE.write({"version": VERSION, "looks": [to_dict(lk) for lk in mine()]})


def put(look: looks.Look) -> bool:
    """Add a look of your own, or replace the one with its key, and save."""
    if look.group != GROUP or not look.key.startswith(KEY_PREFIX):
        raise ValueError(f"not an own look: {look.key}")
    looks.LOOKS[look.key] = look
    return _save()


def remove(key: str) -> bool:
    look = looks.get(key)
    if look is None or look.group != GROUP:
        return False
    del looks.LOOKS[key]
    return _save()


# ── One look as a file, to pass on ──────────────────────────────────────────

def export(look: looks.Look, path: Path) -> None:
    """Write one look to `path`. OSError when it cannot be written."""
    from planner import config

    config.write_json_atomic(Path(path), {FILE_MARK: VERSION, **to_dict(look)})


def import_file(path: Path) -> looks.Look:
    """Read a look exported elsewhere and add it as one of yours. A name or key
    already taken gets a number. ValueError when the file is not a look,
    OSError when it cannot be read."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"not JSON: {exc}") from exc
    if not isinstance(data, dict) or FILE_MARK not in data:
        raise ValueError("not an exported look")
    look = from_dict(data)
    taken = {lk.caption for lk in looks.LOOKS.values()}
    name, n = look.caption, 2
    while name in taken:
        name, n = f"{look.caption} ({n})", n + 1
    look = dataclasses.replace(look, caption=name, key=new_key(name))
    put(look)
    return look
