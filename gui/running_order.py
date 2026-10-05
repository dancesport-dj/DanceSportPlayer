#!/usr/bin/env python3
"""The rows a playlist list holds, in the order they are played.

Every list on the desk — a rounds/heats deck, a theme list, the Eintanzen
panel, a wishlist, a player-only running order — renders as a table of rows, of
which only some are songs. Round and dance headers, spacers and unfilled grid
slots sit between them, so "the songs, in order" and "the row this song is on"
are two different lists that have to be kept in step.

That correspondence was a bare `list[dict | None]` on the table widget, read
directly by eighteen modules. Every one of them had to know the conventions:
None is a header row, a dict with `entry: None` is an empty grid slot, a dict
with `backup: True` is a stacked final-round spare that must not be counted as
a heat. So "the songs of this list" was written out at a dozen call sites and
"the rows holding a song" at eight more — and they had already drifted, one
asking `entry is not None` where its neighbour asked for truthiness.

Row says what one row is; RunningOrder answers the questions asked of the
whole. Both are plain data — no Qt, no table widget — so the ordering rules
can be tested without building a window.
"""
from dataclasses import dataclass, field, replace
from itertools import count

# Row ids, never handed out twice in a run.
_uids = count(1)


@dataclass
class Row:
    """One song row: the track on it and where it sits.

    A row that is NOT a song — a round header, a dance header, a spacer — is
    not a Row at all but a None in the order, because those rows carry nothing
    of their own. An unfilled slot of a rounds/heats grid IS a Row: it has a
    dance, a heat and a place in the draw, it just has no track in it yet.
    """
    entry: object = None            # MusicEntry, or None for an unfilled slot
    dance: str = ""                 # dance code (LW, CC, …) of the slot
    round_name: str = ""            # the round this row belongs to
    h_idx: int = 0                  # heat index within the round
    d_idx: int = 0                  # dance index (the grid column)
    tier: str = ""                  # early / late — how the round picks
    prefer_fresh: bool = False      # round wants unplayed tracks
    strategy: str = ""              # per-round pick strategy
    multi: bool = False             # round dances more than one dance
    backup: bool = False            # a stacked final-round spare, not a heat
    backup_n: int = 0               # 1, 2, … which spare under the slot
    theme: bool = False             # a theme-list / wishlist row
    warmup: bool = False            # an Eintanzen row
    # Which placement of a track this is — minted with the row, carried along
    # when its track moves, handed back after a re-render (RunningOrder.adopt).
    # The play cursor is this id, so the ■ marker follows the track, not a row
    # number. Not part of what a row says: two rows compare by their data.
    uid: int = field(default_factory=lambda: next(_uids), init=False,
                     compare=False, repr=False)

    @property
    def filled(self) -> bool:
        """Is there a track on this row? An empty grid slot is a row without."""
        return self.entry is not None

    @property
    def path_str(self) -> str:
        """The track's path as a string, or "" on an empty slot — the form the
        played / marked / issue sets are keyed by."""
        p = getattr(self.entry, "path", None)
        return str(p) if p else ""

    def slot(self) -> tuple:
        """Where in the draw this row sits: (round, heat, dance column). What
        the stacked backups are stored under, and what an undo compares."""
        return (self.round_name, self.h_idx, self.d_idx)

    def spare(self, entry, n: int) -> "Row":
        """A stacked final-round backup under this slot: same place in the
        draw, a different track, and not counted as a heat."""
        return replace(self, entry=entry, backup=True, backup_n=n)


class RunningOrder:
    """The rows of one list, and the questions asked about them as a whole.

    Indexable and iterable like the list it replaces — a table widget works in
    row numbers and always will — but the walks that every caller used to write
    out are here, asked once and answered the same way everywhere.
    """

    def __init__(self, rows=None):
        self._rows = list(rows or [])

    # ── the sequence the table renders ───────────────────────────────────────
    def __len__(self) -> int:
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def __getitem__(self, i):
        return self._rows[i]

    def __setitem__(self, i, value):
        self._rows[i] = value

    def __delitem__(self, i):
        del self._rows[i]

    def __bool__(self) -> bool:
        return bool(self._rows)

    def __eq__(self, other) -> bool:
        if isinstance(other, RunningOrder):
            return self._rows == other._rows
        return self._rows == other

    def append(self, row):
        self._rows.append(row)

    def insert(self, i, row):
        self._rows.insert(i, row)

    def clear(self):
        self._rows.clear()

    # ── what is on a given row ───────────────────────────────────────────────
    def at(self, row: int) -> Row | None:
        """The Row at a table row number, or None for a header / out of range.
        Bounds-safe: a row number can outlive the render that produced it."""
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def entry_at(self, row: int):
        """The track on a table row, or None if that row holds none."""
        r = self.at(row)
        return r.entry if r is not None else None

    # ── the songs, and where they are ────────────────────────────────────────
    def songs(self) -> list:
        """Every row that holds a track, in playing order."""
        return [r for r in self._rows if r is not None and r.filled]

    def entries(self) -> list:
        """Every track this list holds, in playing order."""
        return [r.entry for r in self.songs()]

    def song_rows(self) -> list:
        """The table row numbers holding a track, in playing order. Index-wise
        parallel to entries() — the pairing the reorders rely on."""
        return [i for i, r in enumerate(self._rows) if r is not None and r.filled]

    def numbered(self) -> list:
        """(row number, Row) for every row holding a track."""
        return [(i, r) for i, r in enumerate(self._rows) if r is not None and r.filled]

    def has_songs(self) -> bool:
        return any(r is not None and r.filled for r in self._rows)

    def song_count(self) -> int:
        return len(self.songs())

    def paths(self) -> set:
        """Every track path in the list, as strings — for the "already in this
        list" checks that keep a drop from adding a second copy."""
        return {r.path_str for r in self._rows
                if r is not None and r.filled and r.path_str}

    def heat_entries(self) -> list:
        """The tracks that are actually danced: the stacked final-round spares
        are in the list but are not heats of it."""
        return [r.entry for r in self._rows
                if r is not None and r.filled and not r.backup]

    def heat_rows(self) -> set:
        """The table row numbers of the danced slots — what a drag may pick up
        and drop into. A theme / wishlist row is not one, and a stacked spare
        sits under a slot rather than being one."""
        return {i for i, r in enumerate(self._rows)
                if r is not None and r.filled and not r.backup and not r.theme}

    # ── the placements, by id ────────────────────────────────────────────────
    def row_of(self, uid) -> int:
        """The table row the placement `uid` sits on, or -1 when it is gone."""
        if uid is not None:
            for i, r in enumerate(self._rows):
                if r is not None and r.uid == uid:
                    return i
        return -1

    def swap(self, a: int, b: int):
        """Swap the tracks on two rows. Each takes its id along, so a playing
        one's marker goes with it."""
        ra, rb = self._rows[a], self._rows[b]
        ra.entry, rb.entry = rb.entry, ra.entry
        ra.uid, rb.uid = rb.uid, ra.uid

    def placements(self) -> list:
        """(id, track, path, slot) of every row holding a track: what `adopt`
        hands the ids back from once the rows are rebuilt or reshuffled."""
        return [(r.uid, r.entry, r.path_str, r.slot()) for r in self.songs()]

    def adopt(self, placements):
        """Give every track row the id its track had in `placements`.

        Matched from the surest to the loosest: the same track in the same
        slot, then the same track anywhere, then the same file in the same
        slot, then the same file (an undo or a restore builds the tracks anew
        from their paths). The slot is what tells two placements of one track
        apart — a Paso Doble danced in the Vorrunde and again in the Finale.
        Each id goes to one row; every row left over is a new placement."""
        keys = (lambda uid, e, p, s: (id(e), s),
                lambda uid, e, p, s: id(e),
                lambda uid, e, p, s: (p, s) if p else None,
                lambda uid, e, p, s: p or None)
        rows = self.songs()
        taken = set()
        got = {}
        for key in keys:
            free = {}
            for pl in placements:
                k = key(*pl)
                if pl[0] not in taken and k is not None:
                    free.setdefault(k, []).append(pl[0])
            for r in rows:
                if id(r) in got:
                    continue
                k = key(r.uid, r.entry, r.path_str, r.slot())
                ids = free.get(k)
                while ids and ids[0] in taken:
                    ids.pop(0)
                if ids:
                    uid = ids.pop(0)
                    taken.add(uid)
                    got[id(r)] = uid
        for r in self._rows:
            if r is not None:
                r.uid = got.get(id(r), next(_uids))
