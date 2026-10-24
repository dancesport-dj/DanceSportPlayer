"""🎧 Pre-listen: a second player on an output of its own.

The deck's player is the hall's music — in Playing mode, and in Planning mode
too while a title runs on — so a title heard from the library pane, the 🏆
pane, the Similar window or the event plan must not take it over. With a
pre-listen output chosen in ⚙ Settings → 🔊 Sound & player, those go to this
player instead — the operator's headphones on a second card (or the second
output pair of one) — and the music keeps running.
"""
import logging

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from shared.audio.playback import device_id, prime_disconnect_notify, quiet_ffmpeg_log

if TYPE_CHECKING:
    from player.widgets.player import PreviewOverlay

log = logging.getLogger("dancesport.gui.audio")


class CuePlayer(QObject):
    """One title at a time on the pre-listen output; `stopped` when it ends
    or is stopped, so the ▶/■ that started it can go back."""

    stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        quiet_ffmpeg_log()
        self._player = QMediaPlayer(self)
        self._out = QAudioOutput(self)
        self._player.setAudioOutput(self._out)
        prime_disconnect_notify(self._player, self._out)
        self._player.mediaStatusChanged.connect(self._on_status)
        self._player.errorOccurred.connect(self._on_error)
        self._path: Path | None = None
        # Its own mini player (a PreviewOverlay), set by the window.
        self.view: PreviewOverlay | None = None

    @property
    def path(self) -> Path | None:
        """The title pre-listening, None while nothing does."""
        return self._path

    @property
    def media_player(self) -> QMediaPlayer:
        return self._player

    @property
    def audio_output(self) -> QAudioOutput:
        return self._out

    def play(self, path: Path, device) -> None:
        """Play `path` on `device` (a QAudioDevice), from the top."""
        if device_id(self._out.device()) != device_id(device):
            self._out.setDevice(device)   # only on a change: it re-opens the card
        self._path = Path(path)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()
        log.info("🎧 Pre-listen\n"
                 "title: %s\n"
                 "output: %s", self._path.stem, device.description())

    def seek(self, delta_ms: int) -> None:
        """Ctrl+←/→: move by delta_ms, kept inside the title."""
        dur = self._player.duration()
        pos = max(0, self._player.position() + delta_ms)
        if dur > 0:
            pos = min(pos, dur)
        self._player.setPosition(pos)

    def stop(self) -> None:
        if self._path is None:
            return
        self._path = None
        self._player.stop()
        # Let go of the file and of the card: nothing is left open on it.
        self._player.setSource(QUrl())
        self.stopped.emit()

    def _on_status(self, status):
        # A file that cannot be decoded never reaches EndOfMedia: without the
        # stop, ▶/■ and the mini player would stay on "playing" for good.
        if status in (QMediaPlayer.MediaStatus.EndOfMedia,
                      QMediaPlayer.MediaStatus.InvalidMedia):
            self.stop()

    def _on_error(self, err, msg: str):
        log.warning("🎧 Pre-listen error\n"
                    "error: %s\n"
                    "detail: %s\n"
                    "title: %s", err, msg, self._path.stem if self._path else "-")
        self.stop()
