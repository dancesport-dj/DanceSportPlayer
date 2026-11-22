"""⏩ Which pitch-kept tempo the music gets (player.audio.pair_route).

An untapped player gets Qt's own (Signalsmith Stretch inside the FFmpeg
backend); a tapped one makes it itself. The choice, for every music stream:

- "qt": Qt's own, the default. The music stays untapped unless the 🎚 EQ
  (or a channel pair) taps it; there Signalsmith makes the tempo, the same
  stretch. Qt starts a new stretcher on every tempo change, a short gap.
- "signalsmith": the same Signalsmith Stretch as Qt's, from sstretch.dll
  (player.audio.stretch_signalsmith), light on the CPU, a tempo change
  without a gap (the stretch holds back ~120 ms when it starts; the card
  queue in pair_route is deep enough to carry that). Taps every music player (AudioDevice.sync_eq). Also
  Rubber Band's stand-in for a title its ffmpeg is not ready for.
- "rubberband": Rubber Band through ffmpeg's filter
  (player.audio.stretch_ffmpeg), where the ffmpeg in use has it. Its beats
  sound crisper, but it costs clearly more CPU (an ffmpeg process per
  tapped player, plus a spare). Taps every music player too.
- "numpy": player.audio.stretch, WSOLA in numpy. Only the stand-in where
  the others are missing; a little less clear.

The choice is module state, set from the settings (AudioDevice.sync). A
stream that is already being stretched keeps its engine; the next title
gets the new one (PairRoute's pump asks `current()` whenever it is idle).
An engine that broke down (ffmpeg gone) is passed over for the session.
"""
import logging

from player.audio import stretch, stretch_ffmpeg, stretch_signalsmith

log = logging.getLogger("dancesport.gui.audio")

QT = "qt"
DEFAULT = QT
ENGINES = (QT, "signalsmith", "rubberband")
FALLBACK = "numpy"

_chosen = DEFAULT
_broken: set[str] = set()


def set_engine(name: str) -> None:
    """From the settings (GUI thread). Rubber Band also asks ffmpeg for its
    filter now, so the audio thread never waits on that; the others never
    need the answer, and asking costs ~125 ms at every start."""
    global _chosen
    _chosen = name if name in ENGINES else DEFAULT
    if _chosen == "rubberband":
        stretch_ffmpeg.available()


def chosen() -> str:
    return _chosen


def taps_music() -> bool:
    """The app makes every music stream's tempo itself: tapped even with
    the EQ off. Qt's own needs no tap."""
    return _chosen != QT


def current() -> str:
    """The engine a new tapped stream gets: the chosen one if it is there,
    else Signalsmith (also Qt's own), else numpy."""
    if (_chosen == "rubberband" and "rubberband" not in _broken
            and stretch_ffmpeg.available()):
        return "rubberband"
    if stretch_signalsmith.available():
        return "signalsmith"
    return FALLBACK


def note_broken(engine: str) -> None:
    """A stream's engine stopped working: not chosen again this session."""
    _broken.add(engine)


def make(sample_rate: int, engine: str | None = None):
    """A stretch for one stream, from `engine` (default: `current()`).
    It carries the name it was built as in `.engine`."""
    engine = engine or current()
    made = None
    if engine == "rubberband":
        try:
            made = stretch_ffmpeg.FfmpegStretch(
                sample_rate, standin=lambda: make(sample_rate, "signalsmith"))
        except (RuntimeError, OSError) as exc:
            log.warning("⏩ Rubber Band stretch failed, Signalsmith stands in\n"
                            "error: %s", exc)
            note_broken("rubberband")
            engine = current()
    if made is None and engine == "signalsmith":
        try:
            made = stretch_signalsmith.SignalsmithStretch(sample_rate)
        except (RuntimeError, OSError) as exc:
            log.warning("⏩ Signalsmith stretch failed, numpy stands in\n"
                            "error: %s", exc)
            engine = FALLBACK
    if made is None:
        made = stretch.TimeStretch(sample_rate)
    made.engine = engine
    return made
