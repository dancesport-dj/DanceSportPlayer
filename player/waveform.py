"""〰 The waveform strip above the player card's seek bar.

The seek bar says where the song is; the strip says what is coming: a quiet
bridge, the break before a Paso Doble highlight, the dead air at the end that
the player skips anyway, and where the ⏳ fade-out of a timed cut begins.

The outline is decoded off the GUI thread. Not a QThread: quitting the app
while one still runs destroys it mid-run and takes the process down (the open
silence-probe issue), and a decode is not worth that risk. A daemon thread
dies with the process instead, and hands its peaks back through a signal,
which Qt queues onto the GUI thread.
"""
import logging
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPolygonF
from PySide6.QtWidgets import QWidget

log = logging.getLogger("dancesport.gui.waveform")

# Slices across the whole file; the strip is never wider than this in pixels
# on a desk monitor, and 600 floats per title is nothing to keep.
_BINS = 600
# Peaks need no fidelity, only the outline: 4 kHz decodes a song in a blink.
_DECODE_SR = 4000
# Titles of the session whose outline is already known (most recent last).
_KEEP = 64

_PLAYED = QColor("#5aa0ff")
_AHEAD = QColor("#3d5578")
_SILENCE = QColor(0, 0, 0, 110)
_MARK = QColor("#b0762a")
_MARK_ARMED = QColor("#ff9800")
_FADE = QColor(216, 160, 160, 110)      # the card's fade-out colour, see-through
# The final seconds: the seek bar's red end warning, on the strip too.
_PLAYED_END = QColor("#e53935")
_AHEAD_END = QColor("#7a3035")
# Where playback is: a slim orange line with a cap at each edge — the caps
# make it read from across the desk and set it apart from a 🐂 mark.
_HEAD = QColor("#ff9800")
_HEAD_EDGE = QColor("#10141d")
_HEAD_W = 1
_CAP_W = 11
_CAP_H = 6


def compute_peaks(path: Path) -> list[float]:
    """The outline of one file, or [] when it cannot be decoded."""
    from shared.audio_probes import decode_pcm_mono, waveform_peaks
    return waveform_peaks(decode_pcm_mono(path, _DECODE_SR), _BINS)


class WaveformLoader(QObject):
    """Peaks per file: from the session, else from the database, else decoded
    on a daemon thread — and then stored, so each title decodes only once."""

    ready = Signal(str, object)     # path, peaks ([] = could not decode)

    def __init__(self, parent=None, compute=compute_peaks,
                 cache_of: Callable[[], object] | None = None):
        super().__init__(parent)
        self._compute = compute
        # The window's AudioCache, looked up late: it arrives with the library.
        self._cache_of = cache_of or (lambda: None)
        self._cache: dict[str, list[float]] = {}
        self._pending: set[str] = set()
        # First receiver, so the cache holds the peaks before anyone asks again.
        self.ready.connect(self.store)

    def request(self, path: Path) -> list[float] | None:
        """The peaks if known, else None — and `ready` follows once decoded."""
        key = str(path)
        if key in self._cache:
            return self._cache[key]
        stored = self._stored(path)
        if stored is not None:
            self._remember(key, stored)
            return stored
        if key not in self._pending:
            self._pending.add(key)
            threading.Thread(target=self._run, args=(key,), daemon=True,
                             name="waveform").start()
        return None

    def _run(self, key: str):
        try:
            peaks = self._compute(Path(key))
        except Exception as exc:        # a decode must never take the desk down
            log.warning("〰 Waveform decode failed\n"
                        "file: %s\n"
                        "error: %s", key, exc)
            peaks = []
        try:
            self.ready.emit(key, peaks)
        except RuntimeError:            # the card went away while it decoded
            pass

    def _stored(self, path: Path) -> list[float] | None:
        db = self._cache_of()
        if db is None:
            return None
        try:
            return db.get_waveform(path)
        except Exception as exc:        # a broken cache only costs the decode
            log.warning("〰 Stored waveform unreadable\n"
                        "file: %s\n"
                        "error: %s", path, exc)
            return None

    def store(self, key: str, peaks: list[float]):
        """Runs on the GUI thread when `ready` lands: keep it for the session
        and, when it decoded, in the database for the next one."""
        self._pending.discard(key)
        self._remember(key, peaks)
        db = self._cache_of()
        if peaks and db is not None:    # [] = no decode today, try again later
            try:
                db.put_waveform(Path(key), peaks)
            except Exception as exc:
                log.warning("〰 Waveform not stored\n"
                            "file: %s\n"
                            "error: %s", key, exc)

    def _remember(self, key: str, peaks: list[float]):
        self._cache.pop(key, None)
        self._cache[key] = peaks
        while len(self._cache) > _KEEP:
            self._cache.pop(next(iter(self._cache)))


class WaveformStrip(QWidget):
    """The outline across the same span as the seek bar: 0 to where playback
    actually ends (the cut, the stop, or the file's end)."""

    seekRequested = Signal(int)     # ms the user let go at
    scrubbed = Signal(int)          # ms under the mouse while it is held

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            "The waveform of the title — what has played is blue, all of it\n"
            "red in the final seconds. The broad orange bar is where it plays.\n"
            "Shaded: silence the player skips · thin orange: Paso Doble\n"
            "highlights · red-tinted: the fade-out of a timed cut.\n"
            "Click to jump there.")
        self._peaks: list[float] | None = None
        self._span = 0          # ms the strip spans (the seek bar's maximum)
        self._dur = 0           # ms of the whole file, which the peaks cover
        self._pos = 0
        self._silences: list[tuple[float, float]] = []
        self._marks: list[int] = []
        self._armed: int | None = None
        self._fade_at: int | None = None
        self._ending = False    # in the final seconds: drawn red
        self._heights: tuple | None = None     # (key, per-pixel heights)
        self._scrubbing = False     # the mouse holds the playhead

    # ── Fed by the card ──

    def set_peaks(self, peaks):
        self._peaks = list(peaks) if peaks is not None else None
        self._heights = None
        self.update()

    def set_span(self, span_ms: int, dur_ms: int):
        span, dur = max(0, int(span_ms)), max(0, int(dur_ms))
        if (span, dur) != (self._span, self._dur):
            self._span, self._dur = span, dur
            self._heights = None
            self.update()

    def set_position(self, ms: int):
        if self._scrubbing:     # the mouse has the playhead, not playback
            return
        self._move_head(ms)

    def _move_head(self, ms: int):
        before = self.x_for(self._pos)
        self._pos = max(0, int(ms))
        if self.x_for(self._pos) != before:     # repaint only when it moves
            self.update()

    def set_silences(self, spans_secs):
        self._silences = [(float(a), float(b)) for a, b in (spans_secs or [])]
        self.update()

    def set_marks(self, marks_ms, armed_ms=None):
        self._marks = [int(m) for m in (marks_ms or [])]
        self._armed = int(armed_ms) if armed_ms else None
        self.update()

    def set_fade_start(self, ms):
        self._fade_at = int(ms) if ms is not None else None
        self.update()

    def set_ending(self, on: bool):
        """Red while the title is in its final seconds, like the seek bar."""
        on = bool(on)
        if on != self._ending:
            self._ending = on
            self.update()

    # ── Geometry ──

    def x_for(self, ms: float) -> int:
        if self._span <= 0:
            return 0
        return round(min(1.0, max(0.0, ms / self._span)) * self.width())

    def ms_for(self, x: float) -> int:
        w = max(1, self.width())
        return round(min(1.0, max(0.0, x / w)) * self._span)

    def _column_heights(self) -> list[float]:
        """The peak under each pixel column, 0..1 — cached per size and span."""
        w = self.width()
        key = (w, self._span, self._dur, id(self._peaks))
        if self._heights is not None and self._heights[0] == key:
            return self._heights[1]
        peaks = self._peaks or []
        n = len(peaks)
        out = []
        if n and self._dur > 0 and w > 0:
            per_ms = n / self._dur
            for x in range(w):
                a = int(self.ms_for(x) * per_ms)
                b = max(a + 1, int(self.ms_for(x + 1) * per_ms))
                out.append(max(peaks[min(a, n - 1):min(b, n)] or [0.0]))
        self._heights = (key, out)
        return out

    # ── Qt ──

    # Scrubbed like the seek bar: the playhead follows the held mouse —
    # clamped, so a drag off the left edge is the very start — and the
    # player seeks once, where the mouse lets go.

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._span > 0:
            self._scrubbing = True
            self._scrub_to(event)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._scrubbing:
            self._scrub_to(event)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._scrubbing and event.button() == Qt.MouseButton.LeftButton:
            self._scrubbing = False
            ms = self.ms_for(event.position().x())
            self._move_head(ms)
            self.seekRequested.emit(ms)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _scrub_to(self, event):
        ms = self.ms_for(event.position().x())
        self._move_head(ms)
        self.scrubbed.emit(ms)
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(Qt.PenStyle.NoPen)
        w, h = self.width(), self.height()
        mid = h / 2
        heights = self._column_heights()
        head = self.x_for(self._pos)
        played, ahead = ((_PLAYED_END, _AHEAD_END) if self._ending
                         else (_PLAYED, _AHEAD))
        if heights:
            for x, v in enumerate(heights):
                bar = max(1.0, v * (h - 4))
                p.setBrush(played if x < head else ahead)
                p.drawRect(QRectF(x, mid - bar / 2, 1, bar))
        else:
            # Not decoded (yet): a hairline, so the strip is not a hole.
            p.setBrush(ahead)
            p.drawRect(QRectF(0, mid - 0.5, w, 1))
        p.setBrush(_SILENCE)
        for a, b in self._silences:
            xa, xb = self.x_for(a * 1000), self.x_for(b * 1000)
            if xb > xa:
                p.drawRect(QRectF(xa, 0, xb - xa, h))
        if self._fade_at is not None and 0 <= self._fade_at < self._span:
            xa = self.x_for(self._fade_at)
            grad = QLinearGradient(xa, 0, w, 0)
            grad.setColorAt(0.0, QColor(_FADE.red(), _FADE.green(), _FADE.blue(), 0))
            grad.setColorAt(1.0, _FADE)
            p.setBrush(grad)
            p.drawRect(QRectF(xa, 0, w - xa, h))
        for m in self._marks:
            if not 0 <= m <= self._span:
                continue
            hot = self._armed is not None and m == self._armed
            mw = 3 if hot else 2
            p.setBrush(_MARK_ARMED if hot else _MARK)
            p.drawRect(QRectF(self.x_for(m) - mw / 2, 0, mw, h))
        if self._span > 0:
            self._paint_head(p, min(max(head, 1), w - 1), h)
        p.end()

    def _paint_head(self, p: QPainter, x: float, h: int):
        """The playhead: an orange line the full height, capped top and bottom
        by a small triangle, outlined dark so it stands out on blue and red."""
        p.setPen(_HEAD_EDGE)
        p.setBrush(_HEAD)
        # The outline takes a pixel each side; the orange inside is _HEAD_W.
        p.drawRect(QRectF(x - _HEAD_W // 2 - 1, 0, _HEAD_W + 1, h - 1))
        half = _CAP_W / 2
        p.drawPolygon(QPolygonF([QPointF(x - half, 0), QPointF(x + half, 0),
                                 QPointF(x, _CAP_H)]))
        p.drawPolygon(QPolygonF([QPointF(x - half, h - 1),
                                 QPointF(x + half, h - 1),
                                 QPointF(x, h - 1 - _CAP_H)]))
        p.setPen(Qt.PenStyle.NoPen)
