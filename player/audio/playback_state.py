"""🎵 What is on the deck right now — the facts every part of the evening reads.

Split off MainWindow, where these were four loose fields written by the player
and read by the loudness, pause, Paso Doble and analysis mixins alike. Holding
them in one object gives them one owner, and a part that is later cut out of
the window takes this one object instead of four window attributes.
"""
from dataclasses import dataclass, field
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
    # 🌅 The music heard (seconds) at which this title's fade-in started;
    # None = no fade-in running.
    fade_in_from: float | None = None
    # 🌅 Seconds of music this title fades in over, 0 = it starts at full
    # level — kept for the waveform after the fade-in is through.
    fade_in_secs: float = 0.0
    # ⏩ The pre-roll seek still owed once the media is open (ms); 0 = none.
    pre_roll_ms: int = 0
    # Titles that would not play this session, path → the backend's reason.
    # Their rows stay red (a live Check-Music issue) until one plays again.
    failed: dict[str, str] = field(default_factory=dict)
    # The load whose setSource errors queued before it may still arrive for:
    # they belong to the title it replaced. None once they are all seen.
    stale_error_token: int | None = None
    # 🧊 The stall watchdog: token, position and since-when it last saw the
    # title stand, and the token of the title it has already reloaded once.
    stall_seen: tuple = (None, 0, 0.0)
    stall_reloaded: int | None = None
    # 🆘 The on-air note last written (deck index, row, path); None = there is
    # none on disk for this title.
    on_air: tuple | None = None
    # 🥇 (token, monotonic start) while a title of the final plays on after
    # its fade; a load or stop moves the token on, which ends it.
    celebrate: tuple | None = None
    # 🌙 The closing song after a planned ⏹ stop while it is on the deck;
    # None once another title takes over.
    closing: Path | None = None
    # 🎶 The token of a title waiting for a background pad to fade out (see
    # _bed_first_ms); the wall counts that wait as music.
    bed_wait: int | None = None
    # ⏱ Start-up latency of the running play request: when the ▶ was handled
    # and whether the "media ready" line has already been logged for it.
    play_t0: float | None = None
    ready_logged: bool = False
