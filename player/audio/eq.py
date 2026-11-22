"""🎚 A room equalizer for the audio a tapped player hands over.

QMediaPlayer has no equalizer. On the FFmpeg backend its decoded audio can be
taken off before Qt's output (a QAudioBufferOutput, see player.audio.pair_route),
and this filters it on the way to the card.

Each band is an RBJ-cookbook biquad: a low cut, shelves at both ends, peaks in
between. scipy is not in the player build and a sample-by-sample IIR loop in
Python is far too slow for several players, so the bands' combined COMPLEX
response is evaluated on a fine frequency grid and turned into one impulse
response. That keeps the biquads' own phase (no added delay), and the filter
runs as an FFT convolution of each piece Qt hands over (overlap-save), the
input's tail carried from one piece to the next so the joins are not heard.

No Qt in here: it takes and gives float32 frames, shape (frames, channels).
"""
import math
from dataclasses import dataclass

import numpy as np

from planner.playing import equalizer as eq_settings
from shared.audio.playback import eq_available

KINDS = ("lowcut", "lowshelf", "peak", "highshelf")
MAX_GAIN_DB = 12.0
# Taps of the impulse response: 170 ms at 48 kHz, long enough for a 30 Hz low
# cut to ring out. The response is computed on a grid this many times finer
# and cut back, so what the IIR still rings past the cut is faded, not folded.
KERNEL_TAPS = 8192
_GRID_FACTOR = 4
_FADE_TAPS = 1024
# Shelf slope S = 1 (the steepest without a bump).
_SHELF_Q = 1 / math.sqrt(2)


@dataclass(frozen=True)
class Band:
    """One band. `gain` in dB (ignored by the low cut, which is on or off),
    `freq` in Hz, `q` the width of a peak / the low cut's resonance."""
    kind: str
    freq: float
    gain: float = 0.0
    q: float = 1.0
    on: bool = True

    def audible(self) -> bool:
        """Whether this band changes the sound at all."""
        if not self.on:
            return False
        return self.kind == "lowcut" or abs(self.gain) >= 0.05


def available() -> bool:
    """Whether this run's backend can have an EQ (shared.audio.playback)."""
    return eq_available()


def bands_for(settings: dict, source: str) -> tuple[Band, ...] | None:
    """`source`'s EQ as the route takes it (PairRoute.set_eq): its bands, ()
    while bypassed, None while off or where this backend has no EQ."""
    cfg = eq_settings.eq_of(settings, source)
    if not available() or not eq_settings.tapped(cfg):
        return None
    return tuple(Band(*b) for b in eq_settings.audible_bands(cfg))


def biquad(band: Band, rate: int) -> tuple[np.ndarray, np.ndarray]:
    """(b, a) of `band` at sample rate `rate`, a normalised to a[0] = 1."""
    w0 = 2 * math.pi * min(band.freq, 0.49 * rate) / rate
    cos, sin = math.cos(w0), math.sin(w0)
    gain = max(-MAX_GAIN_DB, min(MAX_GAIN_DB, band.gain))
    amp = 10 ** (gain / 40)
    if band.kind == "lowcut":
        alpha = sin / (2 * band.q)
        b = [(1 + cos) / 2, -(1 + cos), (1 + cos) / 2]
        a = [1 + alpha, -2 * cos, 1 - alpha]
    elif band.kind == "peak":
        alpha = sin / (2 * band.q)
        b = [1 + alpha * amp, -2 * cos, 1 - alpha * amp]
        a = [1 + alpha / amp, -2 * cos, 1 - alpha / amp]
    elif band.kind in ("lowshelf", "highshelf"):
        alpha = sin / (2 * _SHELF_Q)
        root = 2 * math.sqrt(amp) * alpha
        if band.kind == "lowshelf":
            b = [amp * ((amp + 1) - (amp - 1) * cos + root),
                 2 * amp * ((amp - 1) - (amp + 1) * cos),
                 amp * ((amp + 1) - (amp - 1) * cos - root)]
            a = [(amp + 1) + (amp - 1) * cos + root,
                 -2 * ((amp - 1) + (amp + 1) * cos),
                 (amp + 1) + (amp - 1) * cos - root]
        else:
            b = [amp * ((amp + 1) + (amp - 1) * cos + root),
                 -2 * amp * ((amp - 1) + (amp + 1) * cos),
                 amp * ((amp + 1) + (amp - 1) * cos - root)]
            a = [(amp + 1) - (amp - 1) * cos + root,
                 2 * ((amp - 1) - (amp + 1) * cos),
                 (amp + 1) - (amp - 1) * cos - root]
    else:
        raise ValueError("unknown band kind: %r" % band.kind)
    b, a = np.array(b), np.array(a)
    return b / a[0], a / a[0]


def response(bands, rate: int, freqs) -> np.ndarray:
    """The bands' combined complex response at `freqs` (Hz), headroom left out."""
    z1 = np.exp(-1j * 2 * np.pi * np.asarray(freqs, dtype=float) / rate)
    z2 = z1 * z1
    total = np.ones_like(z1)
    for band in bands:
        if band.audible():
            b, a = biquad(band, rate)
            total *= (b[0] + b[1] * z1 + b[2] * z2) / (a[0] + a[1] * z1 + a[2] * z2)
    return total


def headroom_db(bands, rate: int = 48000) -> float:
    """What the output is turned down by so no boost can clip: the highest
    point of the combined curve (neighbouring bands add up), 0 when nothing
    is raised."""
    if is_flat(bands):
        return 0.0
    freqs = np.geomspace(20, min(20000, 0.49 * rate), 600)
    peak = float(np.max(np.abs(response(bands, rate, freqs))))
    return max(0.0, 20 * math.log10(peak))


def is_flat(bands) -> bool:
    return not any(b.audible() for b in bands)


def design_kernel(bands, rate: int) -> np.ndarray | None:
    """The impulse response (float64, KERNEL_TAPS long) of `bands` with the
    headroom applied, or None when they leave the sound as it is."""
    if is_flat(bands):
        return None
    grid = KERNEL_TAPS * _GRID_FACTOR
    freqs = np.fft.rfftfreq(grid, 1 / rate)
    taps = np.fft.irfft(response(bands, rate, freqs), grid)[:KERNEL_TAPS]
    taps[-_FADE_TAPS:] *= np.cos(np.linspace(0, np.pi / 2, _FADE_TAPS)) ** 2
    return taps * 10 ** (-headroom_db(bands, rate) / 20)


class EqFilter:
    """The EQ for one stream: `process` each piece in order, `reset` when the
    stream jumps (a seek, a stop, a new card). `set_bands` takes effect over
    the next piece, faded from the old sound to the new: no click, no zipper."""

    def __init__(self, channels: int = 2):
        self._channels = channels
        self._rate = 0
        self._bands: tuple[Band, ...] = ()
        self._kernel: np.ndarray | None = None
        # The kernel heard before the last change, until a piece has faded it out.
        self._fading: np.ndarray | None = None
        self._fade_pending = False
        self._spectra: dict[tuple[int, int], np.ndarray] = {}
        self._history = np.zeros((KERNEL_TAPS - 1, channels), dtype=np.float32)

    @property
    def bands(self) -> tuple[Band, ...]:
        return self._bands

    @property
    def active(self) -> bool:
        """Whether the sound is changed (or still fading from a change)."""
        return self._kernel is not None or self._fade_pending

    def set_bands(self, bands, rate: int) -> None:
        bands = tuple(bands)
        if bands == self._bands and rate == self._rate:
            return
        same_card = rate == self._rate
        # Fade from what was last HEARD: a change still waiting for its piece
        # (a slider drag) was never heard, so the fade keeps its own start.
        old = self._fading if self._fade_pending else self._kernel
        self._bands, self._rate = bands, rate
        self._kernel = design_kernel(bands, rate)
        self._spectra.clear()
        # A new rate is a new card: what played before is gone, nothing to fade.
        self._fading = old if same_card else None
        self._fade_pending = self._fading is not None or self._kernel is not None

    def reset(self) -> None:
        """Forget the input so far, and any fade still due."""
        self._history[:] = 0
        self._fading, self._fade_pending = None, False

    def process(self, frames: np.ndarray) -> np.ndarray:
        """`frames` (n, channels) float32 filtered, the same shape."""
        n = len(frames)
        if not n:
            return frames
        if not self.active:
            self._remember(frames)
            return frames
        joined = np.vstack([self._history, frames.astype(np.float32, copy=False)])
        out = self._convolve(joined, self._kernel, n)
        if self._fade_pending:
            before = self._convolve(joined, self._fading, n)
            ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)[:, None]
            out = before + (out - before) * ramp
            self._fading, self._fade_pending = None, False
        self._history = joined[-(KERNEL_TAPS - 1):].copy()
        return out.astype(np.float32, copy=False)

    def _remember(self, frames):
        if len(frames) >= KERNEL_TAPS - 1:
            self._history = frames[-(KERNEL_TAPS - 1):].astype(np.float32)
        else:
            self._history = np.vstack([self._history[len(frames):],
                                       frames.astype(np.float32, copy=False)])

    def _convolve(self, joined, kernel, n):
        """The last `n` frames of `joined` through `kernel` (None = as they are)."""
        if kernel is None:
            return joined[-n:]
        size = 1 << (len(joined) - 1).bit_length()
        key = (id(kernel), size)
        spectrum = self._spectra.get(key)
        if spectrum is None:
            if len(self._spectra) > 8:
                self._spectra.clear()
            spectrum = self._spectra[key] = np.fft.rfft(kernel, size)[:, None]
        full = np.fft.irfft(np.fft.rfft(joined, size, axis=0) * spectrum, size, axis=0)
        return full[len(joined) - n:len(joined)]
