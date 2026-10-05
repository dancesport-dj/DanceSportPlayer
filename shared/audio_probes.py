"""The ffmpeg probes the desk and the evening both run on single files.

Where ffmpeg is, a track's loudness (EBU R128), its silent stretches, its noise
floor, its samples as mono PCM, and the Paso Doble highlight times worked out
from those samples. Plus the three QThreads that run one such probe while a
song plays: SilenceWorker, LoudnessWorker and PdHighlightWorker. The batch
passes over the whole library (gui.workers.LibraryPass) build on these.

Qt only for the threads; no widgets, no librosa, so the player build keeps it.
"""
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from planner.config import INSTALL_DIR
from planner.db import SILENCE_NOISE_DB

log = logging.getLogger("dancesport.workers")

# ─────────────────────────────────────────────────────────────────────────────
# Loudness Analyzer (EBU R128 integrated loudness via ffmpeg)
# ─────────────────────────────────────────────────────────────────────────────

def unpacked_ffmpeg_builds(root: Path) -> list[Path]:
    """The ffmpeg.exe of every gyan essentials build unpacked in `root`, newest
    version first. The folder name carries the version, so any one is found."""
    def version(exe):
        return tuple(int(n) for n in re.findall(r"\d+", exe.parents[1].name))
    return sorted(root.glob("ffmpeg-*-essentials_build/bin/ffmpeg.exe"),
                  key=version, reverse=True)


# Candidate locations for a bundled ffmpeg.exe: next to the app / .exe (where a
# deployed build keeps it), then the full essentials build kept in the dev tree.
# Then the package-manager prefixes a GUI launch does not have on PATH: a .app
# started from Finder or the Dock inherits launchd's /usr/bin:/bin:/usr/sbin:/sbin,
# NOT the shell's PATH, and a desktop launcher on Linux is no better — so a
# Homebrew ffmpeg is installed and still invisible to shutil.which. A path that
# cannot exist on the running platform simply never matches.
_FFMPEG_CANDIDATES = (
    INSTALL_DIR / "ffmpeg.exe",
    *unpacked_ffmpeg_builds(INSTALL_DIR),
    *unpacked_ffmpeg_builds(Path(__file__).parents[1]),
    Path("/opt/homebrew/bin/ffmpeg"),                 # Homebrew, Apple silicon
    Path("/usr/local/bin/ffmpeg"),                    # Homebrew, Intel
    Path("/opt/local/bin/ffmpeg"),                    # MacPorts
    Path("/home/linuxbrew/.linuxbrew/bin/ffmpeg"),    # Homebrew on Linux
    Path.home() / ".linuxbrew" / "bin" / "ffmpeg",    # …its per-user install
)
# Last "I: -xx.x LUFS" line of the ebur128 stderr output = the integrated
# (whole-file) loudness summary; earlier I: lines are the running measurement.
_LUFS_RE = re.compile(r"I:\s*(-?\d+(?:\.\d+)?)\s+LUFS")


def find_ffmpeg() -> str | None:
    """ffmpeg on PATH, else the copy bundled with the project, else the usual
    Homebrew / MacPorts prefixes, else None."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    for cand in _FFMPEG_CANDIDATES:
        if cand.is_file():
            return str(cand)
    return None


def _kill_probe(proc):
    """Kill a probe subprocess if it is still up. Racing a process that just
    exited is normal here, not an error."""
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.kill()
    except OSError:
        pass


def _probeable(path) -> bool:
    """True when `path` is a real file on disk.

    ffmpeg reads an input that isn't a local path as a URL and fetches it. These
    probes take their path from library entries and .m3u lines, and an imported
    playlist may name `http://…` — that line is no file, so it survives as a
    ghost entry carrying the URL. Such a target is refused instead of reaching
    `-i`. A missing file already produced None (ffmpeg just failed), so this
    only skips the pointless decode attempt."""
    try:
        return Path(path).is_file()
    except OSError:
        return False


def _ffmpeg_probe(args: list, path: Path, what: str,
                  on_proc=None) -> tuple[int, str] | None:
    """Run one decode-only ffmpeg pass; return (returncode, stderr) or None.

    `on_proc` is handed the Popen as soon as it exists, so a worker can kill
    the pass when it is cancelled — subprocess.run() offers no handle to kill,
    and these probes decode a whole track."""
    if not _probeable(path):
        return None
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", creationflags=flags)
    except OSError as exc:
        log.warning("%s\nfile: %s\nerror: %s", what, path, exc)
        return None
    if on_proc is not None:
        on_proc(proc)
    try:
        _out, err = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.communicate()
        log.warning("%s\nfile: %s\nerror: %s", what, path, exc)
        return None
    return proc.returncode, err


def measure_lufs(ffmpeg: str, path: Path, on_proc=None) -> float | None:
    """Integrated EBU R128 loudness of one file in LUFS, or None on failure.

    Decodes the file through ffmpeg's ebur128 filter (audio only, null output)
    and parses the summary block from stderr."""
    res = _ffmpeg_probe(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
         "-map", "a:0", "-af", "ebur128", "-f", "null", "-"],
        path, "📊 Loudness probe failed", on_proc)
    if res is None:
        return None
    matches = _LUFS_RE.findall(res[1] or "")
    if not matches:
        return None
    return float(matches[-1])


def decode_pcm_mono(path: Path, sr: int = 22050):
    """The whole file as float32 mono samples at `sr`, decoded by ffmpeg.

    Stands in for `librosa.load`: the player build ships no librosa (and none
    of its numba/scipy stack), and the only thing librosa was doing here was
    turning an mp3 into samples — ffmpeg already decodes every other probe in
    this module. Returns an empty array when there is no ffmpeg, no readable
    file, or the decode failed; every caller treats that as 'no data'."""
    import numpy as np

    ffmpeg = find_ffmpeg()
    if ffmpeg is None or not _probeable(path):
        return np.empty(0, dtype=np.float32)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.Popen(
            [ffmpeg, "-hide_banner", "-nostats", "-v", "quiet",
             "-i", str(path), "-map", "a:0", "-ac", "1", "-ar", str(sr),
             "-f", "f32le", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=flags)
    except OSError as exc:
        log.warning("🎚️ PCM decode failed\n"
                    "file: %s\n"
                    "error: %s", path, exc)
        return np.empty(0, dtype=np.float32)
    try:
        raw, _err = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.communicate()
        log.warning("🎚️ PCM decode timed out\n"
                    "file: %s\n"
                    "error: %s", path, exc)
        return np.empty(0, dtype=np.float32)
    if proc.returncode != 0 or not raw:
        return np.empty(0, dtype=np.float32)
    # A truncated final frame would make frombuffer refuse the whole buffer.
    return np.frombuffer(raw[:len(raw) - len(raw) % 4], dtype="<f4")


def _rms_envelope(y, frame_length: int = 2048, hop_length: int = 512):
    """Per-frame RMS of `y` — what `librosa.feature.rms` returns for its own
    defaults, reproduced so the highlight thresholds below keep their meaning.

    librosa centres the frames, i.e. it zero-pads by half a frame on each side
    so frame k is centred on sample k*hop; the padding is what makes the frame
    count 1 + len(y) // hop rather than something shorter."""
    import numpy as np

    if y.size == 0:
        return np.empty(0, dtype=np.float32)
    pad = frame_length // 2
    padded = np.pad(np.asarray(y, dtype=np.float64), pad, mode="constant")
    n_frames = 1 + (padded.size - frame_length) // hop_length
    if n_frames <= 0:
        return np.empty(0, dtype=np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(
        padded, frame_length)[::hop_length][:n_frames]
    return np.sqrt(np.mean(frames * frames, axis=1)).astype(np.float32)


# ── Silence detection (ffmpeg silencedetect) ────────────────────────────────
# The threshold lives in planner.db: the stored spans are keyed on it, so the
# database drops what an older one probed. 2 s minimum keeps musical breaks
# (Paso Doble stops!) out of the spans.
_SILENCE_NOISE_DB = SILENCE_NOISE_DB
_SILENCE_MIN_SECS = 2.0
_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?\d+(?:\.\d+)?)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?\d+(?:\.\d+)?)")
_FF_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)")


def parse_silences(stderr: str) -> list:
    """Silence spans [[start, end], …] from ffmpeg silencedetect stderr.

    A file that ENDS silent leaves the last silence_start unclosed — close it
    at the stream duration parsed from the same output."""
    text = stderr or ""
    starts = [float(m) for m in _SILENCE_START_RE.findall(text)]
    ends = [float(m) for m in _SILENCE_END_RE.findall(text)]
    if len(starts) > len(ends):
        m = _FF_DURATION_RE.search(text)
        if m:
            h, mi, s = m.groups()
            ends.append(int(h) * 3600 + int(mi) * 60 + float(s))
        else:
            starts = starts[:len(ends)]
    return [[max(0.0, s), e] for s, e in zip(starts, ends) if e > s]


def detect_silences(ffmpeg: str, path: Path, on_proc=None) -> list | None:
    """Silent stretches ≥2 s in one file as [[start, end], …] (empty list — no
    silence), or None on failure. Decode-only ffmpeg pass, read-only."""
    res = _ffmpeg_probe(
        [ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
         "-map", "a:0",
         "-af", f"silencedetect=noise={_SILENCE_NOISE_DB}dB:d={_SILENCE_MIN_SECS}",
         "-f", "null", "-"],
        path, "🔇 Silence probe failed", on_proc)
    if res is None or res[0] != 0:
        return None
    return parse_silences(res[1])


# ── Noise floor (ffmpeg astats) ─────────────────────────────────────────────
# astats' "Noise floor" is the quietest local peak in the whole file: a clean
# digital track gets down to its lead-in silence, while a tape or vinyl rip
# never gets below its own hiss. Measured over 150 random library tracks: half
# reach true silence (−inf), the median is −78 dB, and only ~3 % stay above
# −50 dB — old medleys and anthem rips, exactly the ones that hiss in a quiet
# hall. Nothing is filtered: the number only feeds the 🔇 Check-Music warning.
_NOISE_FLOOR_RE = re.compile(r"Noise floor dB:\s*(-?\d+(?:\.\d+)?|-?inf)")


def parse_noise_floor(stderr: str) -> float | None:
    """Noise floor in dBFS from ffmpeg astats stderr, or None when the output
    holds none. '-inf' (the track reaches digital silence) comes back as
    -math.inf, which compares below every threshold — as it should."""
    m = _NOISE_FLOOR_RE.search(stderr or "")
    if not m:
        return None
    return float(m.group(1))


def measure_noise_floor(ffmpeg: str, path: Path) -> float | None:
    """Noise floor of one file in dBFS, or None on failure. Decode-only ffmpeg
    pass, read-only — the whole file, since the quietest moment can sit
    anywhere in it."""
    if not _probeable(path):
        return None
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
             "-map", "a:0", "-af", "astats=measure_perchannel=none",
             "-f", "null", "-"],
            capture_output=True, text=True, errors="replace",
            timeout=120, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        log.warning("🔇 Noise probe failed\n"
                    "file: %s\n"
                    "error: %s", path, exc)
        return None
    if proc.returncode != 0:
        return None
    return parse_noise_floor(proc.stderr)


class SilenceWorker(QThread):
    """Probes one file's silent stretches in the background, so playback can
    arm the silence skip without blocking the GUI while the song plays."""
    done = Signal(str, list)   # (path as str, spans [[start, end], …])
    error = Signal(str, str)   # (path as str, error message)

    def __init__(self, path: Path, ffmpeg: str, parent=None):
        super().__init__(parent)
        self._path = Path(path)
        self._ffmpeg = ffmpeg
        self._cancel = False
        self._proc = None

    def cancel(self):
        """Kill the ffmpeg pass. run() is a single blocking probe, so unlike
        the batch analyzers there is no per-item loop to check a flag in."""
        self._cancel = True
        _kill_probe(self._proc)

    def _adopt(self, proc):
        self._proc = proc
        if self._cancel:      # cancelled before ffmpeg was even up
            _kill_probe(proc)

    def run(self):
        spans = detect_silences(self._ffmpeg, self._path, on_proc=self._adopt)
        if self._cancel:
            return
        if spans is None:
            self.error.emit(str(self._path), "silence probe failed")
        else:
            self.done.emit(str(self._path), spans)


class LoudnessWorker(QThread):
    """Measures one file's EBU R128 loudness in the background, so a track that
    was never analyzed still gets levelled — a second or two into playing."""
    done = Signal(str, float)   # (path as str, LUFS)
    error = Signal(str, str)    # (path as str, error message)

    def __init__(self, path: Path, ffmpeg: str, parent=None):
        super().__init__(parent)
        self._path = Path(path)
        self._ffmpeg = ffmpeg
        self._cancel = False
        self._proc = None

    def cancel(self):
        """Kill the ffmpeg pass — see SilenceWorker.cancel."""
        self._cancel = True
        _kill_probe(self._proc)

    def _adopt(self, proc):
        self._proc = proc
        if self._cancel:
            _kill_probe(proc)

    def run(self):
        lufs = measure_lufs(self._ffmpeg, self._path, on_proc=self._adopt)
        if self._cancel:
            return
        if lufs is None:
            self.error.emit(str(self._path), "loudness probe failed")
        else:
            self.done.emit(str(self._path), lufs)


# ─────────────────────────────────────────────────────────────────────────────
# Paso Doble highlight detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_pd_highlights(path: Path) -> list:
    """The three choreographed highlight times (seconds) of a Paso Doble track,
    as `[h1, h2, h3]` — h1/h2 may be None when no clear candidate is found,
    h3 falls back to the end of the track.

    A PD highlight is the climax where the music crescendos and then drops away
    dramatically (the couples hit their pose on the crash). Tournament edits
    follow a standardized phrase structure — highlight 1 at roughly one third,
    highlight 2 at two thirds, highlight 3 at the very end — so detection first
    collects "crash" candidates on the smoothed RMS envelope (a loud passage
    collapsing into a sustained deep dip), then picks the strongest candidate
    inside each expected position window (verified on several España Cañí /
    Spanish Gypsy Dance tournament recordings).
    """
    import numpy as np

    sr = 22050
    hop = 512
    y = decode_pcm_mono(path, sr)
    rms = _rms_envelope(y, hop_length=hop)
    if rms.size == 0:
        return []
    win = max(1, int(round(0.3 * sr / hop)))   # ~0.3 s smoothing
    sm = np.convolve(rms, np.ones(win) / win, mode="same")
    ref = float(np.percentile(sm, 95))
    if ref <= 0:
        return []
    norm = sm / ref
    frame_t = hop / sr
    total = len(norm) * frame_t

    pre_w = int(round(2.0 / frame_t))     # the crash needs a loud run-up
    build_w = int(round(5.0 / frame_t))   # crescendo strength context
    cands = []                            # (time, dip seconds, dip depth, build)
    i = pre_w
    while i < len(norm):
        if norm[i] < 0.40 and float(np.max(norm[i - pre_w:i])) >= 0.7:
            j = i
            while j < len(norm) and norm[j] < 0.55:
                j += 1
            dur = (j - i) * frame_t
            depth = float(np.min(norm[i:j])) if j > i else float(norm[i])
            if dur >= 0.5 and depth <= 0.35:
                build = float(np.mean(norm[max(0, i - build_w):i]))
                # a real crash follows a sustained crescendo — dips inside an
                # extended quiet passage have a weak run-up and are skipped
                if build >= 0.55:
                    cands.append((i * frame_t, dur, depth, build))
            i = j + 1
        else:
            i += 1

    def pick(lo: float, hi: float):
        """Strongest candidate inside a relative position window: long, deep
        dips after a sustained crescendo beat short rhythmic breaks."""
        best, best_score = None, 0.0
        for t, dur, depth, build in cands:
            if lo <= t / total <= hi:
                score = min(dur, 2.5) * (0.55 - depth) + 0.25 * build
                if score > best_score:
                    best, best_score = round(t, 2), score
        return best

    h1 = pick(0.25, 0.48)
    h2 = pick(0.52, 0.75)
    h3 = None
    for t, _dur, _depth, _build in cands:   # last crash = the finale
        if t / total >= 0.85:
            h3 = round(t, 2)
    final_crash = h3 is not None
    if h3 is None:
        h3 = round(total, 2)
    return fill_phrased_highlights([h1, h2, h3], Path(path).name, final_crash)


# "España Cañí phrasing, 3 highlights": highlight 1 to 2 is 35 bars, 2 to the
# final crash 43 — as the crash search measures them on the edits it does read
# (43.65 / 78.69 / 121.67 s at 60 bars a minute).
_PHRASING_3_RE = re.compile(
    r"espa[nñ]a[\W_]*ca[nñ][ií][\W_]*phrasing[\W_]+3\s*highlights", re.IGNORECASE)
# "Spanish Gipsy Dance" is the same piece under its English title, and its
# tournament edits follow the same phrasing — mostly without the tag. Only the
# short edits differ, and their names say so.
_SPANISH_GIPSY_RE = re.compile(r"spanish[\W_]+g[iy]psy", re.IGNORECASE)
_SHORT_EDIT_RE = re.compile(r"short|2\s*highlights", re.IGNORECASE)
_BARS_H1_TO_H2 = 35
_BARS_H2_TO_H3 = 43


def fill_phrased_highlights(times: list, name: str, final_crash: bool) -> list:
    """Count the highlights the crash search missed back from the final crash,
    for a track whose name says it follows the España Cañí phrasing with three
    highlights. Some arrangements play on through highlights 1 and 2, so there
    is no dip to hear; the finale crash still is one, and the phrasing fixes
    how many bars lie before it. The bar length is the tempo in the name.

    A highlight the search found within a bar of its phrasing position is
    kept — it is the crash itself, sharper than the count, so the other one is
    counted from it rather than from the end. One further off is an earlier
    or later accent the search mistook for it (by ear: the phrasing hits,
    those picks mostly don't), so the phrasing position replaces it.

    Most tournament Paso Dobles share this phrasing, whatever the name says
    (El Bailador, Vamos Amigos, …). On a track without the tag, a highlight
    landing on its phrasing position is what shows it does."""
    h1, h2, h3 = times
    if not final_crash or _SHORT_EDIT_RE.search(name):
        return times
    from planner.parsing import _detect_bpm
    bpm = _detect_bpm(name)
    if not bpm:
        return times
    bar = 60.0 / bpm

    def near(t, pos):
        return t is not None and abs(t - pos) <= bar

    p2 = h3 - _BARS_H2_TO_H3 * bar
    p1 = p2 - _BARS_H1_TO_H2 * bar
    ok2 = near(h2, p2)
    if ok2:
        p1 = h2 - _BARS_H1_TO_H2 * bar
    ok1 = near(h1, p1)
    if ok1 and not ok2:
        p2 = h1 + _BARS_H1_TO_H2 * bar
    tagged = _PHRASING_3_RE.search(name) or _SPANISH_GIPSY_RE.search(name)
    if not (tagged or ok1 or ok2):
        return times
    return [h1 if ok1 else round(p1, 2), h2 if ok2 else round(p2, 2), h3]


class PdHighlightWorker(QThread):
    """Detects the highlights of one Paso Doble file in the background, so
    arming the highlight stop never blocks the GUI while the song plays."""
    done = Signal(str, list)   # (path as str, highlight times in seconds)
    error = Signal(str, str)   # (path as str, error message)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = Path(path)

    def run(self):
        try:
            times = detect_pd_highlights(self._path)
            self.done.emit(str(self._path), times)
        except Exception as exc:
            log.warning("🐂 Paso Doble highlight detection failed\n"
                        "file: %s\n"
                        "error: %s", self._path, exc)
            self.error.emit(str(self._path), str(exc))
