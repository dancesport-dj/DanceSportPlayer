"""⏩ Signalsmith Stretch for a tapped player: the same pitch-kept tempo Qt's
FFmpeg backend makes on an untapped one, so both sound alike.

Qt compiles Signalsmith Stretch into its FFmpeg plugin (qtmultimedia 6.12
src/3rdparty/signalsmith-stretch, version 1.1.0) and does not export it. The same headers
are vendored in player/audio/native/ and built there, loaded here with
ctypes: sstretch.dll on Windows (in git, build_sstretch.bat),
libsstretch.dylib / libsstretch.so on macOS / Linux (build_sstretch.sh, run
by their app builds; from source run it once). `available()` is False where
the library is missing: player.audio.stretch stands in.

Same calls as player.audio.stretch.TimeStretch. The tempo is the ratio of
frames fed to frames asked for, so a change of tempo carries on seamlessly
(Qt starts a new stretcher on every change, an audible gap). Streaming as
the Signalsmith README describes it: the first inputLatency frames go in by
seek(), the outputLatency frames of pre-roll that follow are dropped, so
nothing is put in front of the title. What it holds back is both halves,
~120 ms of the title at tempo 1 (`lookahead`). At the end,
inputLatency frames of silence carry the processing to the last frame and
flush() gives out the rest.
"""
import ctypes
import logging
import math
import os
import sys

import numpy as np

log = logging.getLogger("dancesport.gui.audio")

_DLL_NAME = {"win32": "sstretch.dll", "darwin": "libsstretch.dylib"}.get(
    sys.platform, "libsstretch.so")
_dll = None
_tried = False


def _load():
    global _dll, _tried
    if _tried:
        return _dll
    _tried = True
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "native", _DLL_NAME)
    if not os.path.isfile(path):
        return None
    try:
        dll = ctypes.CDLL(path)
    except OSError as exc:
        # i18n: data
        log.warning("⏩ Signalsmith stretch not loaded\n"
                        "dll: %s\n"
                        "error: %s", path, exc)
        return None
    vp, fp, i = ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_int
    dll.ss_create.argtypes, dll.ss_create.restype = [i, ctypes.c_float], vp
    dll.ss_destroy.argtypes, dll.ss_destroy.restype = [vp], None
    dll.ss_reset.argtypes, dll.ss_reset.restype = [vp], None
    dll.ss_input_latency.argtypes, dll.ss_input_latency.restype = [vp], i
    dll.ss_output_latency.argtypes, dll.ss_output_latency.restype = [vp], i
    dll.ss_seek.argtypes, dll.ss_seek.restype = [vp, fp, i, ctypes.c_double], None
    dll.ss_process.argtypes, dll.ss_process.restype = [vp, fp, i, fp, i], None
    dll.ss_flush.argtypes, dll.ss_flush.restype = [vp, fp, i], None
    _dll = dll
    return dll


def available() -> bool:
    return _load() is not None


def _ptr(frames: np.ndarray):
    return frames.ctypes.data_as(ctypes.POINTER(ctypes.c_float))


class SignalsmithStretch:
    """One stream's tempo: `process` each piece in order, `reset` when the
    stream jumps (a seek, a stop, a new card), `set_rate` at any time."""

    # The engine that built it, as player.audio.stretch_engines.make names it.
    engine: str = "signalsmith"

    def __init__(self, sample_rate: int = 48000, channels: int = 2):
        dll = _load()
        if dll is None:
            raise RuntimeError(_DLL_NAME + " is not available")
        self._dll = dll
        self._channels = channels
        self._handle = dll.ss_create(channels, float(sample_rate))
        self._in_latency = dll.ss_input_latency(self._handle)
        self._out_latency = dll.ss_output_latency(self._handle)
        self._rate = 1.0
        self.reset()

    def __del__(self):
        handle, self._handle = getattr(self, "_handle", None), None
        if handle:
            self._dll.ss_destroy(handle)

    @property
    def rate(self) -> float:
        return self._rate

    def set_rate(self, rate: float) -> None:
        """The tempo: 1.04 plays 4 % faster. Heard from the next piece on."""
        self._rate = float(rate) if rate and rate > 0 else 1.0

    def reset(self) -> None:
        """Start afresh at the next frame fed: nothing before it is used."""
        self._dll.ss_reset(self._handle)
        self._lead = np.zeros((0, self._channels), dtype=np.float32)
        self._started = False
        self._drop = 0                        # pre-roll frames still to drop
        self._fraction = 0.0                  # output frames owed between pieces

    @property
    def lookahead(self) -> int:
        """Title frames it holds back at most before they are heard: the
        input half, and the output half read at the tempo."""
        return self._in_latency + math.ceil(self._out_latency * self._rate) + 1

    @property
    def holding(self) -> bool:
        """Whether it has started on the stream (and holds a lookahead)."""
        return self._started or len(self._lead) > 0

    def process(self, frames: np.ndarray) -> np.ndarray:
        """`frames` (n, channels) in; whatever is ready comes back, the same
        width (none at all while the first lookahead is still filling)."""
        frames = np.ascontiguousarray(frames, dtype=np.float32)
        if not self._started:
            self._lead = np.vstack([self._lead, frames])
            if len(self._lead) < self._in_latency:
                return self._empty()
            lead, frames = self._lead[:self._in_latency], self._lead[self._in_latency:]
            self._lead = self._empty()
            self._dll.ss_seek(self._handle, _ptr(np.ascontiguousarray(lead)),
                              len(lead), self._rate)
            self._started = True
            self._drop = self._out_latency
            frames = np.ascontiguousarray(frames)
        return self._trim(self._run(frames))

    def flush(self) -> np.ndarray:
        """The title ran out: what it still holds, and start afresh."""
        if not self._started:
            rest = self._lead                 # too short to have begun: as it is
            self.reset()
            return rest
        silence = np.zeros((self._in_latency, self._channels), dtype=np.float32)
        tail = [self._run(silence)]
        out = np.zeros((self._out_latency, self._channels), dtype=np.float32)
        self._dll.ss_flush(self._handle, _ptr(out), len(out))
        tail.append(out)
        rest = self._trim(np.vstack(tail))
        self.reset()
        return rest

    def _run(self, frames: np.ndarray) -> np.ndarray:
        owed = len(frames) / self._rate + self._fraction
        n_out = math.floor(owed)
        self._fraction = owed - n_out
        out = np.zeros((n_out, self._channels), dtype=np.float32)
        if len(frames) or n_out:
            self._dll.ss_process(self._handle, _ptr(frames), len(frames), _ptr(out), n_out)
        return out

    def _trim(self, out: np.ndarray) -> np.ndarray:
        if self._drop:
            cut = min(self._drop, len(out))
            self._drop -= cut
            out = out[cut:]
        return out

    def _empty(self) -> np.ndarray:
        return np.zeros((0, self._channels), dtype=np.float32)
