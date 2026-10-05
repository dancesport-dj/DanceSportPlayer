"""⏸ The pause between two dances — what comes next and when it starts.

Split off MainWindow, where these were loose fields written by the player when
a title ends and read by the pause/announcement mixin while the pause runs.
Holding them in one object gives them one owner and one set of defaults (the
⏯-hold and fade fields used to exist only after the first pause had started).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.playlist_table import PlaylistTable


@dataclass
class BetweenDances:
    """The running pause (if any) and the title it leads into."""

    # (table, row, path) of the NEXT song while a pause runs; None = no pause.
    # Cleared by any manual stop/play.
    pending: tuple[PlaylistTable, int, Path] | None = None
    # Monotonic time that next song starts.
    advance_at: float = 0.0
    # Whether that pause is long enough to be worth showing the hall
    # (see _pause_on_screen): with the ⏸ switch off it lasts one refresh.
    shown: bool = False
    # Set while the operator ⏯-pauses the filler, with the seconds that were
    # left when the hold began.
    held: bool = False
    hold_remaining: float = 0.0
    # Set while ⏭ fades the filler out to skip the rest of the pause.
    fade_end: float | None = None
    # The spoken "next dance" cue: already given for this pause, and the
    # monotonic time the music is held back until after it (_ANNOUNCE_TAIL).
    announced: bool = False
    quiet_until: float = 0.0
    # After a 🏁 round-end stop: the next round's first song, started by
    # tapping the big player's ⏯ (see _start_next_round).
    round_start: tuple[PlaylistTable, int, Path] | None = None
