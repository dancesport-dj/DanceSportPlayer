"""⏸ The pause between two dances — what comes next and when it starts.

Split off MainWindow, where these were loose fields written by the player when
a title ends and read by the pause/announcement mixin while the pause runs.
Holding them in one object gives them one owner and one set of defaults (the
⏯-hold and fade fields used to exist only after the first pause had started).

A 🔀 crossfade is the other way one title hands over to the next — no pause,
the two overlap — so its state is held here too (Crossfade).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtCore import QTimer
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

    from gui.table.playlist_table import PlaylistTable


@dataclass
class Crossfade:
    """The crossfade in flight (if any): the second player, and where the two
    ramps stand. Wired by player/window/main_xfade.py."""

    # The player that is not the deck right now, its output and the ramp's
    # timer, built on first use — most evenings never fade. While a crossfade
    # runs it is the tail that carries the old title out.
    player: QMediaPlayer | None = None
    out: QAudioOutput | None = None
    timer: QTimer | None = None
    # None, or "fading" while the two titles overlap.
    state: str | None = None
    t0: float = 0.0  # when the ramps started
    length: float = 0.0  # how long they run, seconds
    curve: str = "equal"  # their shape (shared.audio.playback.crossfade_levels)
    incoming: Path | None = None  # the incoming title's path
    paused_at: float | None = None  # when ⏯ held both titles, or None
    # Until when the picture's marker walks on past a crossfade that ran its
    # course, to the box's right edge; None when it does not.
    after_until: float | None = None
    # Where the picture's marker stands (shared.xfade_view.CrossfadeView
    # .set_progress), None while it shows none.
    mark: float | None = None


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
    # The spoken "next dance" cue: already given for this pause, and the
    # monotonic time the music is held back until after it (_ANNOUNCE_TAIL).
    announced: bool = False
    quiet_until: float = 0.0
    # After a 🏁 round-end stop: the next round's first song, started by
    # tapping the big player's ⏯ (see _start_next_round).
    round_start: tuple[PlaylistTable, int, Path] | None = None
    # ⏭ auto-advance off: the title put under the cursor when one ended, to
    # be cued once the end has cleared the player (see _cue_next_song).
    cue_next: tuple[PlaylistTable, int, Path] | None = None
    # 🌙 The closing song after a planned ⏹ stop, waiting for the end to
    # release the last title (see _cue_next_song).
    closing: Path | None = None
    # 🔀 The crossfade, where the list walks on with no pause.
    xfade: Crossfade = field(default_factory=Crossfade)
