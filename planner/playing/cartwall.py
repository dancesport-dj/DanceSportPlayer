"""Pure cartwall logic (no Qt): the pad model, the wall document and every
mutation the 🎛 page performs on it.

Extracted so the rules are testable without PySide6 — CartwallWidget renders
what lives here and calls back in; it holds no model of its own.

Pads are keyed by (row, col), never by a linear slot index. The grid is
user-configurable, and a wall that reshuffles itself when you switch 4×4 → 8×6
is a wall you can no longer play from muscle memory. Growing the grid therefore
moves nothing at all; shrinking it relocates only the pads that no longer fit,
and never drops one.
"""
import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

CARTWALL_VERSION = 1

# (cols, rows) offered in the page's grid combo. Tall shapes first: the wall
# lives in a side dock, where there is far more height than width. The file
# format accepts any sane size, so a hand-edited cartwall.json is not punished
# for being unusual.
GRID_SIZES = ((2, 2), (2, 4), (2, 6), (2, 7), (2, 8), (2, 12), (3, 8), (4, 4),
              (4, 8), (6, 4), (8, 2), (8, 4), (8, 6), (10, 6))
DEFAULT_GRID = (2, 8)
_MAX_COLS = 12
_MAX_ROWS = 12

# A fresh wall opens with a second page already there — the page nav is easy to
# miss otherwise, and a wall you did not know had pages is a wall you fill up.
DEFAULT_PAGES = 2

# The ceiling on pages the user can build up to with ➕. Pages are only ever made
# DELIBERATELY now — the nav no longer conjures one when you press ▶ past the end,
# which is how a wall ended up with eleven of them, eight of them empty. Trailing
# empty pages are trimmed on load, so the count cannot creep on its own.
# resize_grid still appends past this rather than lose a pad.
MAX_PAGES = 8

# A sanity cap for reading a corrupt file, so a bad "pages" array cannot make the
# app build thousands of widgets. A multi-drop (fill_pads) stops here too, or
# the pads past it would be saved and never read back, and the grid combo
# refuses a shrink that would need more pages than this.
FILE_PAGE_CAP = 32

# Wall-wide fallback for pads with no colour of their own. White reads as a
# blank card waiting for a label, which is what an unconfigured pad is; the user
# can point it at any colour the pad menu offers.
DEFAULT_PAD_COLOUR = "#ffffff"

# Colours a pad can be given, in the order the colour menu lists them. "" means
# "whatever the wall's default colour is". No BLUE here on purpose: blue is how
# the wall says "this one is running" (light) and "this much has played" (deep),
# and a pad painted in either would lie about its state. Here and not with the
# pad dialog, because ⚙ Settings ▸ 🎛 Cartwall offers them too.
PAD_COLOURS = {
    "Wall default": "",     # white unless the wall was given another one
    "Grey": "#eceff4",
    "Green": "#2f8f4e",
    "Red": "#b23b3b",
    "Olive": "#8a8a2b",
    "Purple": "#7a3fbf",
    "Amber": "#c8871a",
}

# What a starting title does to a running 🎶 background pad, under ⚙ Settings
# ▸ 🎛 Cartwall: "mute" keeps it looping silently under the music, "pause"
# holds it once it is down and carries on from there when the music stops
# (player.audio.cart_voices plays it).
BG_MODES = ("mute", "pause")


def background_pauses(settings: dict) -> bool:
    """True when the 'cart_bg_mode' setting says a title pauses a background
    pad. "stop" is what the option saved before it became pause. Anything else
    reads as the default, which keeps it running."""
    return settings.get("cart_bg_mode") in ("pause", "stop")


# How long a 🎶 background pad takes to come back up once the music stops, and
# to dip to silence when a title starts, under ⚙ Settings ▸ 🎛 Cartwall.
# Seconds to come back, not a snap: the bed swells back in. The dip was once as
# fast as a pad pulls the music down (player.audio.mix._CART_DUCK); Marcel:
# "for fading out over use 0.5s". On the dialog's one-decimal grid.
DEFAULT_BG_FADE_IN_MS = 2000
DEFAULT_BG_FADE_OUT_MS = 500
# …and to come up when it is fired: quick, but never a click; Marcel kept it
# at 0.2 s when the dip went to 0.5 s.
DEFAULT_BG_FIRE_FADE_MS = 200
# 🎶 The volume a pad gets when it is ticked as Background: a bed at full level
# is as loud as the dance music it fills in for. Marcel: "tick backgroud setts
# volume to 50% in the pad … make ist configurable … in the settings".
DEFAULT_BG_VOLUME_PCT = 50
# How long the music has to stay stopped before the bed comes back: the deck
# reports Stopped for a moment between two titles, and a bed swelling up in
# every gap is worse than one that waits; 1.5 s of it read as the bed lagging
# behind the end of the music.
DEFAULT_BG_HOLD_MS = 300


def _bg_fade_ms(settings: dict, key: str, default: int) -> int:
    try:
        ms = int(settings.get(key, default))
    except (TypeError, ValueError):
        return default
    return max(0, min(MAX_FADE_MS, ms))


def background_fade_in_ms(settings: dict) -> int:
    """The 'cart_bg_fade_in_ms' setting, bounded like a pad's fade-out. A broken
    value reads as the default; 0 brings the bed back at once."""
    return _bg_fade_ms(settings, "cart_bg_fade_in_ms", DEFAULT_BG_FADE_IN_MS)


def background_fade_out_ms(settings: dict) -> int:
    """The 'cart_bg_fade_out_ms' setting, the dip under a starting title, read
    like background_fade_in_ms; 0 cuts the bed off at once."""
    return _bg_fade_ms(settings, "cart_bg_fade_out_ms", DEFAULT_BG_FADE_OUT_MS)


def background_fire_fade_ms(settings: dict) -> int:
    """The 'cart_bg_fire_fade_ms' setting, the fade-in of a background pad that
    is fired, read like background_fade_in_ms; 0 starts it at full volume."""
    return _bg_fade_ms(settings, "cart_bg_fire_fade_ms", DEFAULT_BG_FIRE_FADE_MS)


def background_volume(settings: dict) -> float:
    """The 'cart_bg_volume_pct' setting as 0..1: what the pad dialog sets the
    volume to when 🎶 Background is ticked. A broken value reads as the default."""
    try:
        pct = int(settings.get("cart_bg_volume_pct", DEFAULT_BG_VOLUME_PCT))
    except (TypeError, ValueError):
        pct = DEFAULT_BG_VOLUME_PCT
    return max(0, min(100, pct)) / 100


def background_hold_ms(settings: dict) -> int:
    """The 'cart_bg_hold_ms' setting, the wait before a background pad comes
    back once the music stops, read like background_fade_in_ms; 0 = no wait."""
    return _bg_fade_ms(settings, "cart_bg_hold_ms", DEFAULT_BG_HOLD_MS)


def background_quiet_in_pd_wait(settings: dict) -> bool:
    """The 'cart_bg_pd_quiet' setting: a 🎶 background pad stays down while a
    Paso Doble waits for its 'Start after' seconds, as if the music already
    played. On unless switched off — the bed would swell up over the call."""
    return settings.get("cart_bg_pd_quiet", True) is not False


def background_quiet_before_pd(settings: dict) -> bool:
    """Whether a 🎶 background pad stays down between the dance before and a
    Paso Doble (the pause into it, or the PD cued for ⏯). Only with a 'Start
    after' of 0 s: with a wait, that silent wait is the couples' sign and the
    bed dips out for it, so it may come back up in between."""
    return (background_quiet_in_pd_wait(settings)
            and not settings.get("pd_start_delay", 0))


def background_overlaps(settings: dict) -> bool:
    """The 'cart_bg_overlap' setting: a starting title plays over a 🎶
    background pad's fade-out. Off unless switched on — the title waits until
    the bed is down, so its first bar is never under the tail of it."""
    return settings.get("cart_bg_overlap") is True

# Keys that fire the first nine slots of the page on screen. Slot-based, not
# pad-based, so the same finger hits the same corner of the wall on every page;
# a pad that wants a key of its own carries it in CartPad.shortcut and keeps it
# wherever it is moved.
#
# The default only. A wall carries its own list (WallDoc.slot_keys) and may
# rebind every slot and reach past the ninth — Ctrl+digit is a poor fit for a
# desk that already uses those, and a 2×8 wall has sixteen slots.
SLOT_KEYS = tuple(f"Ctrl+{n}" for n in range(1, 10))

# A slot list can name at most one key per cell of the biggest grid.
_MAX_SLOT_KEYS = _MAX_COLS * _MAX_ROWS

LABEL_MAX = 26

# How long a pad takes to let go when it is tapped again or ⏹ stops the wall.
# One setting for the whole wall, because most walls want one answer — and
# overridable per pad, because a three-second fanfare should be gone at once
# while a bed under the Siegerehrung wants seconds. 0 is a hard cut, which
# clicks — allowed, but it is not the default for that reason.
DEFAULT_FADE_MS = 1000
MAX_FADE_MS = 8_000

Cell = tuple[int, int]          # (row, col)
Grid = tuple[int, int]          # (cols, rows)

# "01 - ", "003_", "12." at the front of a filename: track numbering, not a name.
_LEAD_NUM = re.compile(r"^\d{1,3}\s*[\s._-]\s*")
# One trailing "(LW 29)" / "[instr]" group — the library's tempo/genre scaffolding.
_TRAIL_TAG = re.compile(r"\s*[(\[][^()\[\]]*[)\]]\s*$")


@dataclass
class CartPad:
    """One pad. Everything except `path` has a default, so a dropped file is a
    complete pad the moment it lands."""
    path: str
    label: str = ""       # "" → derived from the filename, so a rename fixes it
    colour: str = ""      # "" → the default idle colour
    volume: float = 1.0   # 0.0–1.0 per-pad trim (a background bed at 0.25)
    loop: bool = False    # endless repeat
    duck: bool = True     # pull the deck music down while this pad runs
    # The other way round: the pad goes silent under the deck music while a
    # title plays and comes back up in the pauses. Never together with `duck`.
    # (An old wall's per-pad "dip" level is passed over when it is read.)
    background: bool = False
    stops_others: bool = False   # starting it fades every other running pad out
    shortcut: str = ""    # "" → whatever SLOT_KEYS gives this slot
    # None → follow the wall's fade. An explicit 0 is a hard cut and is NOT the
    # same thing, which is why this cannot be a plain int with a sentinel.
    fade_ms: int | None = None
    # ▶ Place in the wall's pad queue: 0 = not queued, a higher number plays
    # later. On the pad rather than in a list of cells, so every move, swap and
    # turn of the wall carries it along. Only the order counts, not the value.
    queue: int = 0


def fade_for(pad: CartPad, wall_fade: int = DEFAULT_FADE_MS) -> int:
    """How long THIS pad takes to let go: its own override, or the wall's."""
    if pad is None or pad.fade_ms is None:
        return max(0, min(MAX_FADE_MS, int(wall_fade)))
    return max(0, min(MAX_FADE_MS, int(pad.fade_ms)))


@dataclass
class Page:
    name: str = ""
    pads: dict[Cell, CartPad] = field(default_factory=dict)


# ── Labels ────────────────────────────────────────────────────────────────────
def default_label(path) -> str:
    """A pad caption from the filename: no track number, no trailing "(LW 29)",
    underscores as spaces, short enough to read at a glance."""
    stem = Path(str(path)).stem
    name = _TRAIL_TAG.sub("", _LEAD_NUM.sub("", stem)).replace("_", " ")
    name = re.sub(r"\s+", " ", name).strip(" -")
    if not name:
        name = stem.strip() or str(path)
    if len(name) > LABEL_MAX:
        name = name[:LABEL_MAX - 1].rstrip() + "…"
    return name


def pad_title(pad: CartPad) -> str:
    return pad.label or default_label(pad.path)


# ── Cells ─────────────────────────────────────────────────────────────────────
def cell_key(cell: Cell) -> str:
    return f"{cell[0]},{cell[1]}"


def parse_cell(key) -> Cell | None:
    """"3,5" → (3, 5). Anything else → None (a corrupt key, not a pad)."""
    parts = str(key).split(",")
    if len(parts) != 2:
        return None
    try:
        row, col = int(parts[0]), int(parts[1])
    except ValueError:
        return None
    return (row, col) if row >= 0 and col >= 0 else None


def cells_in_order(grid: Grid) -> Iterator[Cell]:
    """Every cell of the grid in reading order — the order free slots are filled."""
    cols, rows = grid
    for row in range(rows):
        for col in range(cols):
            yield (row, col)


def transpose(grid: Grid, pages: list[Page]) -> tuple[Grid, list[Page]]:
    """Turn the wall through a quarter turn: (cols, rows) → (rows, cols) and every
    pad from (row, col) to (col, row).

    This is what a wall does when its dock moves between a side edge and a top
    edge. Transposing the PADS as well as the shape is what makes it lossless and
    exactly reversible — a plain resize would push the pads that no longer fit
    into free slots, and turning back would not bring them home.
    """
    cols, rows = grid
    return ((rows, cols),
            [Page(name=p.name,
                  pads={(col, row): pad for (row, col), pad in p.pads.items()})
             for p in pages])


def is_portrait(grid: Grid) -> bool:
    """Taller than it is wide — the shape a side dock wants."""
    cols, rows = grid
    return rows > cols


def slot_key(grid: Grid, cell: Cell, keys=None) -> str:
    """The keyboard shortcut this cell fires by default, or "" when the wall's
    list does not reach that far. `keys` is the wall's own list; None means the
    stock Ctrl+1…Ctrl+9."""
    cols, rows = grid
    row, col = cell
    if not (0 <= row < rows and 0 <= col < cols):
        return ""
    keys = SLOT_KEYS if keys is None else keys
    slot = row * cols + col
    return keys[slot] if slot < len(keys) else ""


def clean_slot_keys(raw) -> tuple[str, ...]:
    """A slot-key list from a file or a dialog, made safe to bind.

    Entries are kept positionally — slot 3 is index 3 whatever slots 1 and 2
    hold — so a gap is "" rather than a missing element. Anything that is not a
    string becomes "", and trailing blanks are dropped so a list of nothing but
    blanks stores as the empty tuple.

    Not validated as key sequences here: this module has no Qt. The GUI refuses
    an unparseable sequence when it binds (see _add_shortcut), which is the same
    treatment a hand-edited file has always had."""
    if not isinstance(raw, (list, tuple)):
        return SLOT_KEYS
    keys = [s.strip() if isinstance(s, str) else ""
            for s in raw[:_MAX_SLOT_KEYS]]
    while keys and not keys[-1]:
        keys.pop()
    return tuple(keys)


# ── Pages ─────────────────────────────────────────────────────────────────────
def blank_page(name: str = "") -> Page:
    return Page(name=name, pads={})


def new_wall() -> list[Page]:
    """The pages a wall starts life with."""
    return [blank_page() for _ in range(DEFAULT_PAGES)]


def pad_count(pages: list[Page]) -> int:
    return sum(len(p.pads) for p in pages)


def set_pad(pages: list[Page], page: int, cell: Cell, pad: CartPad) -> None:
    pages[page].pads[cell] = pad


def clear_pad(pages: list[Page], page: int, cell: Cell) -> None:
    pages[page].pads.pop(cell, None)


def move_pad(pages: list[Page], src_page: int, src_cell: Cell,
             dst_page: int, dst_cell: Cell) -> None:
    """Drag a pad onto another cell. An occupied target SWAPS rather than
    overwrites — dropping one pad onto another must never destroy the one that
    was already there."""
    if (src_page, src_cell) == (dst_page, dst_cell):
        return
    src = pages[src_page].pads.pop(src_cell, None)
    if src is None:
        return
    victim = pages[dst_page].pads.get(dst_cell)
    pages[dst_page].pads[dst_cell] = src
    if victim is not None:
        pages[src_page].pads[src_cell] = victim


def move_to_page(pages: list[Page], cells: list[tuple[int, Cell]], dst: int,
                 grid: Grid) -> dict[tuple[int, Cell], tuple[int, Cell]]:
    """Move pads onto another page: each into the same cell there when it is
    free, else into the first free one in reading order. A full page takes
    what fits and the rest stay where they were — nothing is overwritten.
    Returns {(page, cell): (dst, cell)} for the pads that moved."""
    moved: dict[tuple[int, Cell], tuple[int, Cell]] = {}
    target = pages[dst]
    for page, cell in cells:
        pad = pages[page].pads.get(cell)
        if page == dst or pad is None:
            continue
        spot = cell if cell not in target.pads else next(
            (c for c in cells_in_order(grid) if c not in target.pads), None)
        if spot is None:
            continue
        del pages[page].pads[cell]
        target.pads[spot] = pad
        moved[(page, cell)] = (dst, spot)
    return moved


# ── The ▶ queue ──────────────────────────────────────────────────────────────
def queued(pages: list[Page]) -> list[tuple[int, Cell, CartPad]]:
    """Every queued pad as (page, cell, pad), in the order it plays."""
    found = [(idx, cell, pad) for idx, page in enumerate(pages)
             for cell, pad in page.pads.items() if pad.queue > 0]
    return sorted(found, key=lambda hit: (hit[2].queue, hit[0], hit[1]))


def queue_ranks(pages: list[Page]) -> dict[tuple[int, Cell], int]:
    """{(page, cell): 1, 2, …} — the number the pad's ≡ badge shows."""
    return {(idx, cell): n
            for n, (idx, cell, _pad) in enumerate(queued(pages), start=1)}


def toggle_queue(pages: list[Page], page: int, cell: Cell,
                 bed_volume: float | None = None) -> bool:
    """Ctrl+click: put the pad at the end of the queue, or take it out.
    Returns whether it is queued now; an empty cell never is.

    A 🎶 pad joining at full volume drops to `bed_volume`, like a tick of
    🎶 Background does (Marcel: "if i have 3 backgroudn items in list queue and
    add a 4 it doent get the 50% value"); a level set by hand stays."""
    pad = pages[page].pads.get(cell)
    if pad is None:
        return False
    if pad.queue:
        pad.queue = 0
        return False
    pad.queue = 1 + max((p.queue for pg in pages for p in pg.pads.values()),
                        default=0)
    if bed_volume is not None and pad.background and pad.volume >= 1.0:
        pad.volume = bed_volume
    return True


def queue_next(pages: list[Page],
               after: int) -> tuple[int, Cell, CartPad] | None:
    """The pad that plays after queue position `after`, wrapping round to the
    first. Keyed on the position, not the cell, so a running pad that was
    moved, taken out or cleared still hands on to the one that followed it.
    A lone queued pad follows itself; nothing queued is None."""
    order = queued(pages)
    if not order:
        return None
    return next((hit for hit in order if hit[2].queue > after), order[0])


def fill_pads(pages: list[Page], page: int, cell: Cell,
              paths: list[str], grid: Grid) -> list[tuple[int, Cell]]:
    """Drop a whole library selection on one pad.

    The cell you aimed at always takes the first track — that is what a
    single-file drop already does, and an aimed drop landing somewhere else
    would be baffling. The rest go into the following FREE cells in reading
    order, spilling onto later pages rather than overwriting pads that are
    already set up. It stops at the page cap a saved wall is read back with, so
    nothing it reports placed is lost on the next start. Returns the cells that
    were filled, so the UI can say how many landed and where.
    """
    if not paths:
        return []
    filled: list[tuple[int, Cell]] = []
    order = list(cells_in_order(grid))
    try:
        start = order.index(cell)
    except ValueError:      # the aimed cell is outside this grid
        start = 0
    pages[page].pads[cell] = CartPad(path=paths[0])
    filled.append((page, cell))

    rest = iter(paths[1:])
    path = next(rest, None)
    idx, cells = page, order[start + 1:]
    while path is not None:
        if idx >= len(pages):
            if len(pages) >= FILE_PAGE_CAP:
                break          # the wall is full: the rest did not land
            pages.append(blank_page())
        target = pages[idx]
        for spot in cells:
            if spot not in target.pads:
                target.pads[spot] = CartPad(path=path)
                filled.append((idx, spot))
                path = next(rest, None)
                if path is None:
                    break
        idx += 1
        cells = order          # every later page starts from its first cell
    return filled


def trim_pages(pages: list[Page]) -> list[Page]:
    """Drop trailing pages that hold nothing and were never named. Always keeps
    one page, so the wall is never page-less."""
    out = list(pages)
    while len(out) > 1 and not out[-1].pads and not out[-1].name:
        out.pop()
    return out or [blank_page()]


def enforce_page_cap(pages: list[Page], grid: Grid) -> list[Page]:
    """Bring a wall back to MAX_PAGES where the pads allow it.

    Trailing empty pages go first, and on a wall reshaped by an older build that
    is the whole job — it could collect a dozen of them. Only past the cap are
    the last page's pads packed into the free cells before it. A page whose pads
    have nowhere to go is KEPT: never a licence to drop a pad. Pages the user
    added on purpose and filled therefore survive a reload; an empty unnamed one
    does not, which is what stops the count creeping.
    """
    out = trim_pages(pages)
    while len(out) > MAX_PAGES:
        tail = out[-1]
        room = sum(grid[0] * grid[1] - len(p.pads) for p in out[:-1])
        if len(tail.pads) > room:
            break                     # it does not fit — the page stays
        homeless = [tail.pads[cell] for cell in sorted(tail.pads)]
        for page in out[:-1]:
            homeless = _fill_free_cells(page, grid, homeless)
        if homeless:
            break                     # cannot happen, but never lose a pad
        out.pop()
    return out


def pack_one_page(pages: list[Page], grid: Grid) -> tuple[list[Page], bool]:
    """Bring the whole wall onto page 1, when the grid has room for it.

    Page 1's own pads do not move — the cells the operator learned stay the cells
    they are — and the later pages fill the free ones in reading order. Returns
    `(pages, False)` untouched when they do not all fit: a wall that has to lose
    four pads to become one page is not a wall the user asked for.
    """
    cols, rows = grid
    if pad_count(pages) > cols * rows:
        return pages, False
    first = Page(name=pages[0].name, pads=dict(pages[0].pads))
    loose = [page.pads[cell] for page in pages[1:] for cell in sorted(page.pads)]
    _fill_free_cells(first, grid, loose)
    return [first], True


def resize_grid(pages: list[Page], grid: Grid) -> tuple[list[Page], int]:
    """Fit every pad into `grid`, relocating the ones that fall outside it.

    Growing the grid is a no-op for every pad. Shrinking it relocates whatever no
    longer fits — **onto its own page first**: a page of ceremony samples that
    still fits the new shape must stay one page of ceremony samples, or the wall
    the operator memorised is gone. Only what a page genuinely cannot hold spills
    forward, adding a page as the last resort: losing a pad built for a
    tournament would be far worse than a wall one page longer than expected.
    Returns the pages plus how many pads moved, so the UI can say so out loud.
    """
    cols, rows = grid
    kept: list[Page] = []
    loose: list[list[CartPad]] = []
    for page in pages:
        fits: dict[Cell, CartPad] = {}
        spilled: list[CartPad] = []
        for cell in sorted(page.pads):
            row, col = cell
            if row < rows and col < cols:
                fits[cell] = page.pads[cell]
            else:
                spilled.append(page.pads[cell])
        kept.append(Page(name=page.name, pads=fits))
        loose.append(spilled)
    if not kept:
        kept = [blank_page()]
    moved = sum(len(batch) for batch in loose)
    if not moved:
        return kept, 0

    # Pass one: every page keeps what it can. Pass two — and only then — takes
    # what is genuinely homeless forward.
    homeless: list[CartPad] = []
    for idx, batch in enumerate(loose):
        homeless += _fill_free_cells(kept[idx], grid, batch)
    page_idx = 0
    while homeless:
        if page_idx >= len(kept):
            kept.append(blank_page())
        homeless = _fill_free_cells(kept[page_idx], grid, homeless)
        page_idx += 1
    return kept, moved


def _fill_free_cells(page: Page, grid: Grid,
                     pads: list[CartPad]) -> list[CartPad]:
    """Drop `pads` into this page's free cells, in reading order. Returns the
    ones that did not fit."""
    queue = list(pads)
    for cell in cells_in_order(grid):
        if not queue:
            break
        if cell not in page.pads:
            page.pads[cell] = queue.pop(0)
    return queue


def missing_paths(pages: list[Page], exists=os.path.isfile) -> set[tuple[int, Cell]]:
    """Which pads point at a file that is not there right now — a stick that came
    up as a different drive letter, say. They are marked, never removed."""
    gone = set()
    for idx, page in enumerate(pages):
        for cell, pad in page.pads.items():
            if not exists(pad.path):
                gone.add((idx, cell))
    return gone


def remap_pads(pages: list[Page], remap,
               exists=os.path.isfile) -> list[tuple[int, Cell, str, str]]:
    """Re-point the pads whose file is gone at what `remap(path)` finds instead.

    The wall is filled once and then played from muscle memory for years, so a
    move to another PC must not cost the operator sixteen re-drops. Only pads
    that are actually missing are touched, and only when the remapper answers —
    `remap` returns a path that exists or None. Mutates the pads in place and
    returns the (page, cell, old, new) it changed, for the caller's summary."""
    done: list[tuple[int, Cell, str, str]] = []
    for idx, cell in sorted(missing_paths(pages, exists)):
        pad = pages[idx].pads[cell]
        found = remap(pad.path)
        if found is None or str(found) == pad.path:
            continue
        done.append((idx, cell, pad.path, str(found)))
        pad.path = str(found)
    return done


# ── The document ──────────────────────────────────────────────────────────────
def _pad_from_dict(data) -> CartPad | None:
    if not isinstance(data, dict):
        return None
    path = data.get("path")
    if not isinstance(path, str) or not path.strip():
        return None
    try:
        volume = float(data.get("volume", 1.0))
    except (TypeError, ValueError):
        volume = 1.0
    fade = data.get("fade_ms")
    if fade is not None:
        try:
            fade = max(0, min(MAX_FADE_MS, int(fade)))
        except (TypeError, ValueError):
            fade = None     # unreadable → follow the wall, not a silent 0
    queue = data.get("queue", 0)
    if not isinstance(queue, int) or isinstance(queue, bool) or queue < 0:
        queue = 0
    return CartPad(
        path=path,
        label=str(data.get("label", "") or ""),
        colour=str(data.get("colour", "") or ""),
        volume=max(0.0, min(1.0, volume)),
        loop=bool(data.get("loop", False)),
        duck=bool(data.get("duck", True)),
        background=bool(data.get("background", False)),
        stops_others=bool(data.get("stops_others", False)),
        shortcut=str(data.get("shortcut", "") or ""),
        fade_ms=fade,
        queue=queue)


def _pad_to_dict(pad: CartPad) -> dict:
    """Only what differs from the defaults, so the file stays readable."""
    out: dict[str, Any] = {"path": pad.path}
    if pad.label:
        out["label"] = pad.label
    if pad.colour:
        out["colour"] = pad.colour
    if pad.volume != 1.0:
        out["volume"] = round(pad.volume, 3)
    if pad.loop:
        out["loop"] = True
    if not pad.duck:
        out["duck"] = False
    if pad.background:
        out["background"] = True
    if pad.stops_others:
        out["stops_others"] = True
    if pad.shortcut:
        out["shortcut"] = pad.shortcut
    if pad.fade_ms is not None:
        out["fade_ms"] = int(pad.fade_ms)
    if pad.queue:
        out["queue"] = pad.queue
    return out


def _grid_from(data) -> Grid:
    try:
        cols, rows = int(data.get("cols")), int(data.get("rows"))
    except (AttributeError, TypeError, ValueError):
        return DEFAULT_GRID
    if 1 <= cols <= _MAX_COLS and 1 <= rows <= _MAX_ROWS:
        return (cols, rows)
    return DEFAULT_GRID


class WallDoc(NamedTuple):
    """What a cartwall.json says. A NamedTuple rather than a dataclass so a
    caller may index it. New fields go LAST and carry a default — a full
    positional unpack still has to name every one of them."""
    grid: Grid
    pages: list[Page]
    page: int
    colour: str
    ok: bool                # False = do not write over this file
    fade_ms: int = DEFAULT_FADE_MS
    slot_keys: tuple[str, ...] = SLOT_KEYS


def load_doc(data) -> WallDoc:
    """The wall a parsed cartwall.json describes.

    `ok` False means "do not write over this file": either it is a version this
    build does not understand, or it is not a wall document at all. A newer
    version must survive being opened by an older build.
    """
    if data is None:
        return WallDoc(DEFAULT_GRID, new_wall(), 0, DEFAULT_PAD_COLOUR, True)
    if not isinstance(data, dict) or data.get("version") != CARTWALL_VERSION:
        return WallDoc(DEFAULT_GRID, new_wall(), 0, DEFAULT_PAD_COLOUR, False)

    grid = _grid_from(data)
    raw_pages = data.get("pages")
    pages: list[Page] = []
    if isinstance(raw_pages, list):
        for raw in raw_pages[:FILE_PAGE_CAP]:
            if not isinstance(raw, dict):
                continue
            pads: dict[Cell, CartPad] = {}
            raw_pads = raw.get("pads")
            if isinstance(raw_pads, dict):
                for key, value in raw_pads.items():
                    cell = parse_cell(key)
                    pad = _pad_from_dict(value)
                    if cell is not None and pad is not None:
                        pads[cell] = pad
            pages.append(Page(name=str(raw.get("name", "") or ""), pads=pads))
    if not pages:
        pages = [blank_page()]

    # A file saved on a bigger grid is a normal thing to open, not an error.
    pages, _moved = resize_grid(pages, grid)
    # An older build's resize left a page per spill, most of them empty. Opening
    # such a wall must give back the two pages the nav offers, not eleven.
    pages = enforce_page_cap(pages, grid)
    try:
        page = int(data.get("page", 0))
    except (TypeError, ValueError):
        page = 0
    # A wall saved before the wall-wide colour existed opens in the standard
    # colour, not in some other grey nobody chose.
    colour = str(data.get("default_colour", "") or DEFAULT_PAD_COLOUR)
    try:
        fade = max(0, min(MAX_FADE_MS, int(data.get("fade_ms",
                                                    DEFAULT_FADE_MS))))
    except (TypeError, ValueError):
        fade = DEFAULT_FADE_MS
    # A wall saved before the slot keys were editable keeps Ctrl+1…Ctrl+9.
    slot_keys = (clean_slot_keys(data["slot_keys"]) if "slot_keys" in data
                 else SLOT_KEYS)
    return WallDoc(grid, pages, max(0, min(page, len(pages) - 1)), colour, True,
                   fade, slot_keys)


def dump_doc(grid: Grid, pages: list[Page], page: int,
             default_colour: str = DEFAULT_PAD_COLOUR,
             fade_ms: int = DEFAULT_FADE_MS,
             slot_keys=SLOT_KEYS) -> dict:
    cols, rows = grid
    doc = {
        "version": CARTWALL_VERSION,
        "cols": cols,
        "rows": rows,
        "page": max(0, min(page, len(pages) - 1)) if pages else 0,
        "pages": [{"name": p.name,
                   "pads": {cell_key(c): _pad_to_dict(pad)
                            for c, pad in sorted(p.pads.items())}}
                  for p in pages],
    }
    if default_colour:
        doc["default_colour"] = default_colour
    if fade_ms != DEFAULT_FADE_MS:
        doc["fade_ms"] = max(0, min(MAX_FADE_MS, int(fade_ms)))
    keys = clean_slot_keys(slot_keys)
    if keys != SLOT_KEYS:
        doc["slot_keys"] = list(keys)
    return doc


# ── carrying a wall between machines ─────────────────────────────────────────
WALL_SUFFIX = ".cartwall.json"


def write_wall(path, doc: dict) -> None:
    """Export: the same document the autosave writes, at a place the user picked.

    Plain and not atomic on purpose — this is a copy onto a stick, not the state
    file the app depends on, and a half-written export is the user's to retry."""
    Path(path).write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")


def read_wall(path) -> WallDoc:
    """Import: parse a file the user picked, with load_doc's guarantees.

    A file that is not a wall this build understands comes back with ok=False,
    exactly like a bad cartwall.json — the caller must not put it on screen."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return WallDoc(DEFAULT_GRID, new_wall(), 0, DEFAULT_PAD_COLOUR, False)
    return load_doc(data)
