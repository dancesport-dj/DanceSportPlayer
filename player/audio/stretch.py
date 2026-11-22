"""⏩ A tempo change that keeps the pitch, for the audio a tapped player hands over.

On the tapped path (player.audio.pair_route) the audio is taken off before
Qt's own pitch-kept time stretch, so a tempo other than 1 has to be made
here. This is WSOLA: short Hann-windowed segments of the title, overlapped
half on half. The segments are read `rate` times as far apart as they are
laid down, and each one is moved by up to ±_SEARCH_MS to wherever it best
continues the one before it. That keeps the waveform's phase across the
joins and the pitch where it was.

Streaming: `process` takes the pieces in order and hands back what is
ready. It holds a window and a search span of lookahead (~55 ms at
40/12 ms). Over a whole title it gives out the input frames ÷ `rate`, with
no drift. At rate 1 every segment lies where the last one left off, the
windows add up to exactly 1, and the sound comes out unchanged.

No Qt in here: it takes and gives float32 frames, shape (frames, channels).
"""
import math

import numpy as np

_WINDOW_MS = 40
_SEARCH_MS = 12
# Below this the tempo counts as 1: segments are not moved at all.
_UNITY = 1e-3


class TimeStretch:
    """One stream's tempo: `process` each piece in order, `reset` when the
    stream jumps (a seek, a stop, a new card), `set_rate` at any time."""

    # The engine that built it, as player.audio.stretch_engines.make names it.
    engine: str = "numpy"

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        self._channels = channels
        half = max(16, int(sample_rate * _WINDOW_MS / 2000))
        self._hop = half                      # frames laid down per segment
        self._size = 2 * half                 # one segment
        self._search = int(sample_rate * _SEARCH_MS / 1000)
        # Periodic Hann: the two halves of neighbouring segments add up to 1.
        n = np.arange(self._size)
        self._window = (0.5 - 0.5 * np.cos(2 * np.pi * n / self._size)).astype(
            np.float32)[:, None]
        self._fft = 1 << (self._size + 2 * self._search + self._size - 1).bit_length()
        self._rate = 1.0
        self.reset()

    @property
    def rate(self) -> float:
        return self._rate

    def set_rate(self, rate: float) -> None:
        """The tempo: 1.04 plays 4 % faster. Heard from the next segment on."""
        self._rate = float(rate) if rate and rate > 0 else 1.0

    def reset(self) -> None:
        """Start afresh at the next frame fed: nothing before it is used."""
        self._buf = np.zeros((0, self._channels), dtype=np.float32)
        self._start = 0                       # title frame of _buf[0]
        # The last segment laid down starts at _prev. A segment one hop
        # earlier than the first frame stands in for it, so the first one
        # is not faded in.
        self._prev = -self._hop
        self._pos = 0.0                       # where the next segment is read from
        self._tail: np.ndarray | None = None

    @property
    def lookahead(self) -> int:
        """Title frames it holds back at most before they are heard."""
        return self._size + 2 * self._search + self._hop

    @property
    def holding(self) -> bool:
        """Whether it has started on the stream (and holds a lookahead)."""
        return self._tail is not None or len(self._buf) > 0

    def flush(self) -> np.ndarray:
        """The title ran out: what it still holds, from where it stands on at
        tempo 1 (no lookahead left to search), and start afresh."""
        hop = self._hop
        rest = self._at(self._prev + hop, len(self._buf)).copy()
        if self._tail is not None:
            # The last segment's second half and the title as it goes on add up to it.
            n = min(hop, len(rest))
            rest[:n] = rest[:n] * self._window[:n] + self._tail[:n]
        self.reset()
        return rest

    def process(self, frames: np.ndarray) -> np.ndarray:
        """`frames` (n, channels) in; whatever is ready comes back, the same
        width (none at all while the lookahead is still filling)."""
        if len(frames):
            self._buf = np.vstack([self._buf, frames.astype(np.float32, copy=False)])
        out = []
        while self._ready():
            out.append(self._step())
        self._trim()
        if not out:
            return np.zeros((0, self._channels), dtype=np.float32)
        return np.vstack(out)

    # ── one segment ──────────────────────────────────────────────────────────

    def _end(self) -> int:
        return self._start + len(self._buf)

    def _at(self, frame: int, n: int) -> np.ndarray:
        i = frame - self._start
        return self._buf[i:i + n]

    def _unity(self) -> bool:
        return abs(self._rate - 1.0) < _UNITY

    def _ready(self) -> bool:
        natural = self._prev + self._hop
        need = natural + self._size
        if not self._unity():
            need = max(need, math.ceil(self._pos) + self._search + self._size)
        return self._end() >= need

    def _step(self) -> np.ndarray:
        hop, size = self._hop, self._size
        natural = self._prev + hop
        if self._tail is None:
            # The stand-in segment's second half: the title's first hop.
            self._tail = self._at(natural, hop) * self._window[hop:]
        if self._unity():
            best = natural
            self._pos = float(natural)
        else:
            best = self._best(natural)
        seg = self._at(best, size) * self._window
        out = self._tail + seg[:hop]
        self._tail = seg[hop:]
        self._prev = best
        self._pos += hop * self._rate
        return out

    def _best(self, natural: int) -> int:
        """The read position within ±_search of where the tempo puts it whose
        segment best continues the last one (normalised cross-correlation of
        the mono mix: both channels move by the same frames)."""
        size = self._size
        lo = max(self._start, round(self._pos) - self._search)
        hi = round(self._pos) + self._search
        if hi < lo:
            return lo
        target = self._at(natural, size).mean(axis=1)
        region = self._at(lo, hi - lo + size).mean(axis=1)
        spec = np.fft.rfft(region, self._fft) * np.conj(np.fft.rfft(target, self._fft))
        corr = np.fft.irfft(spec, self._fft)[:hi - lo + 1]
        energy = np.concatenate([[0.0], np.cumsum(region.astype(np.float64) ** 2)])
        norm = np.sqrt(np.maximum(energy[size:] - energy[:-size], 1e-12))
        return lo + int(np.argmax(corr / norm[:len(corr)]))

    def _trim(self):
        keep = min(self._prev + self._hop, math.floor(self._pos) - self._search)
        drop = keep - self._start
        if drop > 0:
            self._buf = self._buf[drop:]
            self._start = keep
