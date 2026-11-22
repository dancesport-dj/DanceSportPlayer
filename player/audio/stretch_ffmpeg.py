"""⏩ Rubber Band for a tapped player, through ffmpeg's `rubberband` filter.

Rubber Band is GPL, so it is not linked into the app: it runs inside an
ffmpeg process. That is the ffmpeg.exe shipped next to the app on Windows,
the user's own (Homebrew, apt) on macOS and Linux; `available()` asks it
once whether it has the filter.

One process per stream:
- the title goes in over a local TCP socket (ffmpeg connects to us),
- the stretched title comes back on its stdout,
- the tempo is on its command line, so the title is right from its first
  frame. A spare process is kept waiting at the current tempo; a tempo
  change while nothing plays replaces the spare (on a thread of its own:
  starting ffmpeg takes ~150 ms).
- A change mid-title goes in on stdin as ffmpeg's interactive command
  "c" + "rubberband -1 tempo X" (the filter's tempo is runtime-changeable).
  ffmpeg only reads it once audio flows through the filter, and only once
  per -stats_period, hence the short one; it is sent once output has come
  back, which proves the filter is there.

Measured (scratchpad probes, ffmpeg 9.0.2): exact frame counts, the start
within ±4 ms, ~150 ms of the title held back (190 at most), a change
mid-title ~16 ms late, the tail drained in ~12 ms.

Same calls as player.audio.stretch.TimeStretch. Nothing waits for ffmpeg
except the drain at a title's end. A title that starts while no spare is
ready at its tempo, or whose process dies, goes through the stand-in
(Signalsmith from player.audio.stretch_engines) instead; a dead process
also sets `failed`, so the next streams get another engine.
"""
import contextlib
import logging
import socket
import subprocess
import sys
import threading
import time
from typing import IO, cast

import numpy as np

log = logging.getLogger("dancesport.gui.audio")

# Held back at most, in seconds of the title (measured 0.19; margin on top).
_LOOKAHEAD_S = 0.25
_CONNECT_TIMEOUT_S = 5.0
# The tail drains in ~12 ms (measured); a hung ffmpeg must not hold the
# audio thread for long.
_DRAIN_TIMEOUT_S = 0.5

def _ffmpeg() -> str | None:
    from shared.audio.audio_probes import find_ffmpeg
    return find_ffmpeg()


def _no_window() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def available(name: str = "rubberband") -> bool:
    """Whether the ffmpeg this app uses has the filter (asked once)."""
    from shared.audio.audio_probes import ffmpeg_has_filter
    return ffmpeg_has_filter(name)


class _Process:
    """One running ffmpeg at tempo `rate`: a socket in, stdout out, stdin
    for tempo changes. Starting it takes ~150 ms: not on the audio thread."""

    def __init__(self, exe: str, name: str, sample_rate: int, channels: int, rate: float):
        self.rate = rate
        self.width = 4 * channels
        self._out = bytearray()
        self._lock = threading.Lock()
        self.closed = threading.Event()
        self.output_started = False
        self.conn: socket.socket | None = None
        self._connected = threading.Event()
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        server.settimeout(_CONNECT_TIMEOUT_S)
        raw = ["-f", "f32le", "-ar", str(sample_rate), "-ac", str(channels)]
        cmd = [exe, "-hide_banner", "-loglevel", "error", "-nostats", "-stats_period", "0.05",
               "-fflags", "nobuffer", "-probesize", "32", "-analyzeduration", "0",
               *raw, "-i", "tcp://127.0.0.1:%d" % server.getsockname()[1],
               "-af", "%s=tempo=%.6f" % (name, rate), "-flush_packets", "1", *raw, "pipe:1"]
        try:
            self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.DEVNULL, bufsize=0,
                                         creationflags=_no_window())
        except OSError:
            server.close()
            raise
        # Both are PIPE above.
        self._stdin = cast(IO[bytes], self.proc.stdin)
        self._stdout = cast(IO[bytes], self.proc.stdout)
        self._server = server
        self._name = name
        threading.Thread(target=self._accept, daemon=True).start()
        threading.Thread(target=self._read, daemon=True).start()

    def _accept(self):
        try:
            conn, _ = self._server.accept()
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.conn = conn
        except OSError:
            self.conn = None
        finally:
            self._server.close()
            self._connected.set()

    def _read(self):
        while True:
            chunk = self._stdout.read(16384)
            if not chunk:
                break
            with self._lock:
                self._out += chunk
            self.output_started = True
        self.closed.set()

    def ready(self, timeout: float = 0) -> bool:
        """Connected and running (waits up to `timeout` seconds)."""
        self._connected.wait(timeout)
        return self.conn is not None and self.alive()

    def alive(self) -> bool:
        return self.proc.poll() is None

    def send(self, frames: np.ndarray) -> None:
        if self.conn is None:   # sent only once ready(): ffmpeg never connected
            raise OSError("ffmpeg is not connected")
        self.conn.sendall(frames.tobytes())

    def tempo(self, rate: float) -> None:
        self._stdin.write(b"c")
        self._stdin.write(b"%s -1 tempo %.6f\n" % (self._name.encode(), rate))
        self._stdin.flush()

    def take(self) -> bytes:
        with self._lock:
            n = len(self._out) // self.width * self.width
            data = bytes(self._out[:n])
            del self._out[:n]
        return data

    def finish(self) -> bytes:
        """No more title: let ffmpeg drain, and what is left."""
        if self.conn is not None:
            with contextlib.suppress(OSError):
                self.conn.shutdown(socket.SHUT_WR)
        self.closed.wait(_DRAIN_TIMEOUT_S)
        rest = self.take()
        self.kill()
        return rest

    def kill(self) -> None:
        if self.conn is not None:
            with contextlib.suppress(OSError):
                self.conn.close()
        with contextlib.suppress(OSError):
            self._stdin.close()
        if self.proc.poll() is None:
            with contextlib.suppress(OSError):
                self.proc.kill()
        with contextlib.suppress(OSError, subprocess.TimeoutExpired):
            self.proc.wait(1)
        with contextlib.suppress(OSError):
            self._stdout.close()


class FfmpegStretch:
    """One stream's tempo through an ffmpeg filter (rubberband): `process`
    each piece in order, `reset` when the stream jumps, `set_rate` any time.
    `standin` builds the stretch for a title ffmpeg cannot take (default:
    numpy's)."""

    # The engine that built it, as player.audio.stretch_engines.make names it.
    engine: str = "rubberband"

    def __init__(self, sample_rate: int = 48000, channels: int = 2, name: str = "rubberband",
                 standin=None):
        exe = _ffmpeg()
        if not exe or not available(name):
            raise RuntimeError("ffmpeg with the %s filter is not available" % name)
        self._exe, self._name = exe, name
        self._sample_rate, self._channels = sample_rate, channels
        self._make_standin = standin or self._numpy_standin
        self._rate = 1.0
        self._sent_rate = 1.0
        self._started = False
        self.failed = False
        self._closed = False
        self._proc: _Process | None = None
        self._standin = None
        # The spare and its spawning are shared with the spawn thread.
        self._lock = threading.Lock()
        self._spare: _Process | None = None
        self._spawning = False
        self._want_spare()

    def __del__(self):
        self.close()

    def close(self) -> None:
        """Every process gone; a spawn still under way is killed when done."""
        self._closed = True
        lock = getattr(self, "_lock", None)
        if lock is None:   # __init__ stopped before anything was started
            return
        with lock:
            spare, self._spare = self._spare, None
        for proc in (self._proc, spare):
            if proc is not None:
                proc.kill()

    def _numpy_standin(self):
        from player.audio.stretch import TimeStretch
        return TimeStretch(self._sample_rate, self._channels)

    # ── the spare ────────────────────────────────────────────────────────────

    def _want_spare(self) -> None:
        """A spare at the current tempo, started unless one is (one spawn at a
        time: a fader drag spawns once more at its end, not on every step)."""
        with self._lock:
            if self._closed or self.failed or self._spawning:
                return
            if self._spare is not None and self._spare.rate == self._rate:
                return
            self._spawning = True
        threading.Thread(target=self._spawn, args=(self._rate,), daemon=True,
                         name="ffmpeg-stretch-spawn").start()

    def _spawn(self, rate: float) -> None:
        try:
            proc = _Process(self._exe, self._name, self._sample_rate, self._channels, rate)
        except OSError as exc:
            proc = None
            self._fail("could not start ffmpeg: %s" % exc)
        with self._lock:
            self._spawning = False
            old, self._spare = self._spare, proc
            if self._closed:
                self._spare, old = None, proc
        if old is not None:
            old.kill()
        if proc is not None and not self._closed and rate != self._rate:
            self._want_spare()

    def ready(self, timeout: float = 0) -> bool:
        """Whether the next title gets ffmpeg: a spare at the current tempo,
        connected (waits up to `timeout` seconds for it)."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                spare = self._spare
            if spare is not None and spare.rate == self._rate:
                return spare.ready(max(0.0, deadline - time.monotonic()))
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.02)

    # ── the stream ───────────────────────────────────────────────────────────

    def _fail(self, why: str) -> None:
        if not self.failed:
            log.warning("⏩ %s stretch stopped, Signalsmith takes over\n"
                        "reason: %s", self._name, why)
        self.failed = True

    @property
    def rate(self) -> float:
        return self._rate

    def set_rate(self, rate: float) -> None:
        """The tempo: 1.04 plays 4 % faster. A running title gets it on its
        next piece; the spare is replaced to start the next title right."""
        self._rate = float(rate) if rate and rate > 0 else 1.0
        if self._standin is not None:
            self._standin.set_rate(self._rate)
        self._want_spare()

    @property
    def lookahead(self) -> int:
        """Title frames it holds back at most before they are heard."""
        return int(_LOOKAHEAD_S * self._sample_rate)

    @property
    def holding(self) -> bool:
        return self._started or (self._standin is not None and self._standin.holding)

    def reset(self) -> None:
        """Start afresh: the running process is dropped, the spare takes over."""
        if self._proc is not None:
            self._proc.kill()
            self._proc = None
        self._standin = None
        self._started = False
        self._want_spare()

    def process(self, frames: np.ndarray) -> np.ndarray:
        frames = np.ascontiguousarray(frames, dtype=np.float32)
        if self._standin is not None:
            return self._standin.process(frames)
        proc = self._proc
        if proc is None:
            with self._lock:
                proc = self._spare
                if (proc is None or proc.rate != self._rate or not proc.ready()
                        or self.failed):
                    proc = None
                else:
                    self._spare = None
            if proc is None:
                if not self.failed:
                    log.info("⏩ %s not ready at tempo %.3f, Signalsmith takes this title",
                             self._name, self._rate)
                return self._stand_in(frames)
            self._proc, self._sent_rate = proc, proc.rate
            self._want_spare()
        try:
            if self._sent_rate != self._rate and proc.output_started:
                proc.tempo(self._rate)
                self._sent_rate = self._rate
            if len(frames):
                proc.send(frames)
                self._started = True
        except OSError as exc:
            return self._hand_over(proc, frames, str(exc))
        if not proc.alive():
            return self._hand_over(proc, frames, "ffmpeg exited")
        return self._frames(proc.take())

    def _stand_in(self, frames: np.ndarray) -> np.ndarray:
        self._standin = self._make_standin()
        self._standin.set_rate(self._rate)
        return self._standin.process(frames)

    def _hand_over(self, proc: _Process, frames: np.ndarray, why: str) -> np.ndarray:
        """The process died mid-title: the rest of it through the stand-in
        (what ffmpeg still held is lost, a short skip). Passing the title on
        unstretched would pile up `rate` × real time on the card."""
        self._fail(why)
        self._proc = None
        rest = self._frames(proc.take())
        proc.kill()
        self._started = False
        return np.vstack([rest, self._stand_in(frames)])

    def flush(self) -> np.ndarray:
        """The title ran out: what is still held, and a spare for the next."""
        if self._standin is not None:
            rest = self._standin.flush()
            self._standin = None
        else:
            proc, self._proc = self._proc, None
            rest = self._frames(proc.finish()) if proc is not None else self._frames(b"")
        self._started = False
        self._want_spare()
        return rest

    def _frames(self, data: bytes) -> np.ndarray:
        return np.frombuffer(data, dtype=np.float32).reshape(-1, self._channels).copy()
