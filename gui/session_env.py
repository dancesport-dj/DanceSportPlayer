#!/usr/bin/env python3
"""What a saved session IS — the shape of one autosave / undo snapshot.

An env is the whole working session written down: sixteen serialized decks
(eight 🅰–🅷 planning decks, eight 🄰–🄷 day decks), four wishlists, the
Eintanzen panel, the deck names, the 🔒/🔓/✋ modes and the view state. It goes
to autosave_playlist.json and it is also one step on the undo timeline, so an
undo is "apply an older env" and a toast is "what differs between two envs".

The dict is flat — `deck_a` … `day_h`, `wishlist` … `wishlist4` — with the
names and modes in parallel sub-dicts under the same keys. Which of the twenty
keys are grid decks, which are ordered lists, and which of them a given walk
has to cover was written out at every call site: `_build_env` wrote them,
`_apply_env` and `_restore_playlist` read them twice over, and the undo
description walked them three more times. One of those walks covered eight
decks where the others covered sixteen, so a swap inside a 📅 day deck came
back as "view / settings change".

SessionEnv is that knowledge in one module: the keys, the walks over them, the
tracks a serialized deck holds, and the difference between two snapshots said
in words. It is plain dicts in and strings out — no Qt, no window — so what an
undo step will tell the operator is answerable without building one.
"""
from collections import Counter
from pathlib import Path

from planner import i18n
from planner.parsing import _clean_title

# The eight planning decks 🅰–🅷, the eight 📅 day decks 🄰–🄷, the four
# wishlists. Order matters: it is zipped against the tables in that same order.
DECK_KEYS = ("deck_a", "deck_b", "deck_c", "deck_d",
             "deck_e", "deck_f", "deck_g", "deck_h")
DAY_KEYS = ("day_a", "day_b", "day_c", "day_d",
            "day_e", "day_f", "day_g", "day_h")
WISH_KEYS = ("wishlist", "wishlist2", "wishlist3", "wishlist4")
ALL_DECK_KEYS = DECK_KEYS + DAY_KEYS


def deck_paths(deck_env: dict | None) -> list:
    """Every track path a serialized deck holds, incl. the stacked backups."""
    if not deck_env:
        return []
    if deck_env.get("mode") == "Theme":
        return [p for p in (deck_env.get("theme_entries") or []) if p]
    out = []
    for r in (deck_env.get("rounds") or []):
        for cols in (r.get("grid") or {}).values():
            out += [v for v in cols.values() if v]
        for paths in (r.get("backups") or {}).values():
            out += list(paths)
    return out


def deck_slots(deck_env: dict | None) -> dict:
    """Every FILLED grid slot of a serialized deck → its track:
    (round_name, h_idx, d_idx) → path. A theme deck has no grid → empty."""
    slots = {}
    if not deck_env or deck_env.get("mode") == "Theme":
        return slots
    for r in (deck_env.get("rounds") or []):
        rn = str(r.get("name") or "")
        for h, cols in (r.get("grid") or {}).items():
            for d, p in cols.items():
                if p:
                    slots[(rn, str(h), str(d))] = p
    return slots


def list_moved(before: list, after: list) -> list:
    """Tracks of an ordered list sitting at a different position than before."""
    return [p for i, p in enumerate(after) if i >= len(before) or before[i] != p]


def track_label(path: str) -> str:
    """Short, human song name for an undo/redo message, from the filename."""
    try:
        stem = Path(path).stem
        return _clean_title(stem) or stem
    except Exception:
        return str(path)


def fmt_track_list(paths: list) -> str:
    """Name up to two changed tracks; summarise the rest with a count."""
    labels = [track_label(p) for p in paths]
    n = len(labels)
    if n == 1:
        return f"“{labels[0]}”"
    if n == 2:
        return i18n.t("“%s” and “%s”") % (labels[0], labels[1])
    return i18n.t("%s tracks (“%s”, “%s”, …)") % (n, labels[0], labels[1])


class SessionEnv:
    """One saved session, asked questions instead of indexed by key."""

    def __init__(self, data: dict | None = None):
        self.raw = data or {}

    def __bool__(self) -> bool:
        return bool(self.raw)

    def deck(self, key: str) -> dict | None:
        """The serialized deck under `key`, or None if that deck was empty."""
        return self.raw.get(key)

    def decks(self) -> list:
        """(key, serialized deck) for all sixteen decks — day decks included.
        The one walk; a caller that covered only eight is what hid the day-deck
        move from the undo toast."""
        return [(k, self.raw.get(k)) for k in ALL_DECK_KEYS]

    def ordered_lists(self) -> list:
        """(key, paths) for everything held as a plain running order — the four
        wishlists and the Eintanzen panel — where position, not slot, is what a
        track can move within."""
        out = [(k, [p for p in (self.raw.get(k) or []) if p]) for k in WISH_KEYS]
        warm = (self.raw.get("warmup") or {}).get("paths") or []
        out.append(("warmup", [p for p in warm if p]))
        return out

    def holds_tracks(self) -> bool:
        """Is anything actually in this session? An env of nothing but view
        state is not worth writing over the last real autosave. The Eintanzen
        panel counts too: the player-first layout holds nothing else."""
        return (any(self.raw.get(k) for k in ALL_DECK_KEYS)
                or any(paths for _key, paths in self.ordered_lists()))

    def all_paths(self) -> Counter:
        """Multiset of every track in the session — decks, wishlists, panel."""
        c: Counter = Counter()
        for _key, denv in self.decks():
            c.update(deck_paths(denv))
        for _key, paths in self.ordered_lists():
            c.update(paths)
        return c

    def moved_from(self, before: "SessionEnv") -> list:
        """Tracks sitting in a different slot / position than in `before` —
        asked when the multisets match, i.e. a pure move / swap / reorder."""
        moved = []
        for key, after_deck in self.decks():
            before_deck = before.deck(key)
            if ((before_deck or {}).get("mode") == "Theme"
                    or (after_deck or {}).get("mode") == "Theme"):
                moved += list_moved(deck_paths(before_deck),
                                    deck_paths(after_deck))
                continue
            was = deck_slots(before_deck)
            moved += [p for slot, p in deck_slots(after_deck).items()
                      if was.get(slot) != p]
        was_lists = dict(before.ordered_lists())
        for key, paths in self.ordered_lists():
            moved += list_moved(was_lists.get(key) or [], paths)
        seen = set()
        return [p for p in moved if not (p in seen or seen.add(p))]

    def describe_change_from(self, before: "SessionEnv") -> str:
        """Best-effort, human summary of what an undo/redo step did, for the
        toast and the ↶/↷ tooltip — so the operator sees WHICH track changed."""
        bc = before.all_paths()
        ac = self.all_paths()
        added = list((ac - bc).elements())
        removed = list((bc - ac).elements())
        if added and not removed:
            return i18n.t("restored %s") % fmt_track_list(added)
        if removed and not added:
            return i18n.t("removed %s") % fmt_track_list(removed)
        if added and removed:
            return i18n.t("replaced %s → %s") % (fmt_track_list(removed),
                                                 fmt_track_list(added))
        if before and self:
            moved = self.moved_from(before)
            if moved:
                return i18n.t("moved %s") % fmt_track_list(moved)
            if before.raw.get("names") != self.raw.get("names"):
                return i18n.t("playlist rename")
            if before.raw.get("deck_count") != self.raw.get("deck_count"):
                return i18n.t("deck layout change")
        return i18n.t("view / settings change")
