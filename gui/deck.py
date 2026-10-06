#!/usr/bin/env python3
"""What the window knows about one playlist deck.

A deck is a PlaylistTable plus the things that belong to it: the letter badge
that survives a rename, the title the user typed and the one to fall back to,
the header it is written in, the box the header and the table sit in, the two
buttons on that header, its badges, whether it is folded to a tab, and the
generation context (dance, class, rounds…) it was last generated with.

All of that used to live in eleven dicts keyed by the table widget, filled and
read in thirteen modules. Nothing said what a deck consists of — you found that
out by grepping for the next `dict[PlaylistTable, …]` — and every one of them
could be missing an entry for a table the others knew about, so almost every
read was a `.get()` with a default standing in for a deck that does not exist.

Wishlists and the Eintanzen panel are decks too: they use fewer of the fields
(a wishlist shows a title count, a deck shows a Σ total time), which is a
difference between decks, not a reason for a second kind of them.
"""
from dataclasses import dataclass, field


@dataclass
class DeckContext:
    """What one deck was generated with — mode, combos, the grid it drew, and
    the 'Past Competitions' / theme state behind it.

    It lives on the deck, not on the window: the window reads and writes the
    FOCUSED deck's context through its DeckFields (`self._style` …), and code
    that finishes later writes its own deck's context without touching the
    focus. It used to be fifteen window attributes copied out to the deck and
    back in on every focus change."""
    # The generation engine's mode ("Favorites"/"Theme"); ui_mode is the actual
    # ConfigPanel selection ("Favorites"/"Theme"/"Past Competitions"). Past
    # Competitions runs the Favorites engine, so its UI mode is kept apart to
    # bring the right combo back when the deck regains focus.
    mode: str = "Favorites"
    ui_mode: str = "Favorites"
    style: str = "Latin"
    age: str = "Hauptgruppe"
    dance_class: str = "S"
    dances: list = field(default_factory=list)
    playlist: dict | None = None
    theme_entries: list = field(default_factory=list)
    theme_label: str = ""
    # 'Past competitions' live-regen context (set by _generate_replay)
    replay_label: str | None = None
    replay_active: bool = False
    replay_rounds: list | None = field(default_factory=list)
    replay_pools: list | None = None
    replay_use_timbre: bool = True
    active_replay_idx: int | None = None

    def carried_over(self, ui_mode: str) -> "DeckContext":
        """The context a never-generated deck starts with when it gets the
        focus: the combos stay as the user left them on the deck before, so a
        schedule is ready for the next competition without re-picking; the
        content starts empty, so nothing leaks in from that deck."""
        return DeckContext(
            mode="Theme" if ui_mode == "Theme" else "Favorites", ui_mode=ui_mode,
            style=self.style, age=self.age, dance_class=self.dance_class,
            dances=self.dances, replay_rounds=None,
            replay_use_timbre=self.replay_use_timbre)


class DeckField:
    """One DeckContext field, read and written on the window as `_<field>`.

    `self._style = "Standard"` on the window lands in the focused deck's
    context — the window keeps no copy that could go stale."""

    def __set_name__(self, owner, name):
        self.field = name.lstrip("_")

    def __get__(self, win, owner=None):
        if win is None:
            return self
        return getattr(win._focused_ctx(), self.field)

    def __set__(self, win, value):
        setattr(win._focused_ctx(), self.field, value)


@dataclass
class Deck:
    """One playlist deck and everything the window keeps about it."""
    table: object
    letter: str = ""              # 🅰–🅷 / 🄰–🄷 badge, fixed, survives a rename
    name: str = ""                # the title shown, renamable
    default_name: str = ""        # the title a clear resets to
    header: object = None         # QLabel carrying the title
    box: object = None            # container holding header + table (folds)
    mode_btn: object = None       # 🔒/🔓/✋ static → dynamic → free
    fold_btn: object = None       # ▾/▸ fold-to-tab toggle
    total_lbl: object = None      # Σ total-time badge (decks)
    count_lbl: object = None      # title-count badge (wishlists)
    badge_row: object = None      # the bar under the table: badge + ⏭/✋ switch
    folded: bool = False          # folded down to its header tab?
    active: bool = False          # focused, so its header carries the ● dot?
    ctx: DeckContext | None = None   # generation context; None = never generated

    @property
    def title(self) -> str:
        """What to call this deck in a report or a file name."""
        return self.name or self.default_name or "Playlist"
