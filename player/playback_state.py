"""🎵 What is on the deck right now — the facts every part of the evening reads.

Split off MainWindow, where these were four loose fields written by the player
and read by the loudness, pause, Paso Doble and analysis mixins alike. Holding
them in one object gives them one owner, and a part that is later cut out of
the window takes this one object instead of four window attributes.
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PlaybackState:
    """The title loaded on the deck and the generation of that load."""

    # The loaded file; None = nothing on the deck.
    path: Path | None = None
    # Its competition code ("LW", "PD", …, or a social dance's), "" if none.
    dance: str = ""
    # Bumped on EVERY play/stop, so a watchdog or late callback that carries
    # an older token silently no-ops once the operator has moved on.
    token: int = 0
    # File time the 🔇 stillness skip jumped over on this title. It counts as
    # position but nobody danced to it, so the timed cut subtracts it again
    # (see audible_played_secs) — otherwise a silent intro shortens the round.
    offset_ms: int = 0
