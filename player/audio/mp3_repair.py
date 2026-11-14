"""🔧 A repaired copy of an mp3 the ffmpeg backend takes for something else.

A 320 kbps CBR mp3 without a Xing/Info frame can hold a few stray 00 00 01 E0
byte runs. ffmpeg then scores the file as an MPEG program stream, gives it a
length of some 77 000 s and "finishes" it at once, without an error, while
Explorer and Windows Media Foundation play it fine. A leading Info frame (and,
for a large ID3 tag, the tag taken off) makes it read the file as mp3.

The original is never written: the repair is a copy in the temp folder.
"""
import contextlib
import hashlib
import logging
import os
import stat
import sys
import tempfile
import time
from pathlib import Path

log = logging.getLogger(__name__)

# Layer 3 only, indexed by the header's bitrate / sample-rate field.
_BITRATES_V1 = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
_BITRATES_V2 = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
_RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}
_SCAN_BYTES = 65536   # how far behind the tag the first frame is looked for
# 🧹 A copy unused this long goes at the start (a title that needs it again is
# repaired again); a .part this old was left by a crash, not being written.
KEEP_DAYS = 7
_PART_STALE_S = 3600


def tag_size(data: bytes) -> int:
    """Bytes the leading ID3v2 tag takes, 0 without one."""
    if data[:3] != b"ID3" or len(data) < 10:
        return 0
    s = data[6:10]
    return 10 + ((s[0] & 0x7F) << 21 | (s[1] & 0x7F) << 14 | (s[2] & 0x7F) << 7
                 | (s[3] & 0x7F)) + (10 if data[5] & 0x10 else 0)


def frame_at(data: bytes, i: int):
    """(frame length, offset of the Info marker) of the layer-3 frame whose
    header starts at `i`, None if there is none."""
    if i < 0 or i + 4 > len(data) or data[i] != 0xFF or data[i + 1] & 0xE0 != 0xE0:
        return None
    version, layer = (data[i + 1] >> 3) & 3, (data[i + 1] >> 1) & 3
    br, sr, pad = data[i + 2] >> 4, (data[i + 2] >> 2) & 3, (data[i + 2] >> 1) & 1
    if version == 1 or layer != 1 or br in (0, 15) or sr == 3:
        return None
    mono = (data[i + 3] >> 6) == 3
    if version == 3:
        size = 144 * _BITRATES_V1[br] * 1000 // _RATES[3][sr] + pad
        side = 17 if mono else 32
    else:
        size = 72 * _BITRATES_V2[br] * 1000 // _RATES[version][sr] + pad
        side = 9 if mono else 17
    return size, 4 + side


def first_frame(data: bytes, start: int):
    """Offset of the first frame at or after `start` that a second frame
    follows, None if there is none."""
    for i in range(start, min(len(data) - 4, start + _SCAN_BYTES)):
        frame = frame_at(data, i)
        if frame is not None and frame_at(data, i + frame[0]) is not None:
            return i
    return None


def copies_dir() -> Path:
    """The folder the repaired copies live in. On Windows the temp dir is the
    user's own already; a shared POSIX temp dir gets a folder per user, or
    another user could make it first and hand in the copies."""
    base = Path(tempfile.gettempdir())
    if sys.platform == "win32":
        return base / "danceplaylist_repaired"
    return base / f"danceplaylist_repaired-{os.getuid()}"


def _private(folder: Path, make: bool = False) -> bool:
    """`folder` is there (made, with `make`) and only this user can write
    to it. Always so on Windows, see copies_dir."""
    if sys.platform == "win32":
        if make:
            folder.mkdir(parents=True, exist_ok=True)
        return folder.is_dir()
    if make:
        with contextlib.suppress(FileExistsError):
            folder.mkdir(mode=0o700)
    try:
        st = folder.lstat()
    except OSError:
        return False
    return (stat.S_ISDIR(st.st_mode) and st.st_uid == os.getuid()
            and not st.st_mode & 0o022)


def prune_copies(now: float | None = None) -> int:
    """Remove the copies unused for KEEP_DAYS and the .part files a crash
    left. Only those two kinds, only in copies_dir(). How many went."""
    now = time.time() if now is None else now
    gone = 0
    try:
        entries = list(copies_dir().iterdir())
    except OSError:
        return 0          # no folder yet: nothing was ever repaired
    for p in entries:
        limit = {".mp3": KEEP_DAYS * 86400, ".part": _PART_STALE_S}.get(p.suffix)
        try:
            if limit is not None and now - p.stat().st_mtime > limit:
                p.unlink()
                gone += 1
        except OSError:
            continue      # in use by another instance: next start
    if gone:
        log.info("🧹 Old repaired copies removed\n"
                 "count: %d\n"
                 "folder: %s", gone, copies_dir())
    return gone


def _reuse(out: Path) -> Path:
    """A copy found again counts as used now, so prune_copies keeps it."""
    with contextlib.suppress(OSError):
        os.utime(out)
    return out


def _copy_path(path: Path) -> Path:
    """Where the copy of `path` lives: keyed by path, size and time, so a changed
    file gets a new one."""
    st = path.stat()
    key = hashlib.sha1(f"{path}|{st.st_size}|{st.st_mtime_ns}".encode("utf-8",
                       "surrogatepass")).hexdigest()[:16]
    return copies_dir() / f"{key}.mp3"


def cached_copy(path: Path) -> Path | None:
    """The copy an earlier run made of this very file, None if there is none.
    Makes nothing: a title that never needed one stays a plain file."""
    try:
        out = _copy_path(path)
        return _reuse(out) if out.exists() and _private(out.parent) else None
    except OSError:
        return None


def repaired_copy(path: Path) -> Path | None:
    """The copy of `path` with an Info frame in front and no ID3 tag, None if
    the file cannot be read or holds no mp3 frame. A copy made before for the
    same file (same size and time) is reused."""
    try:
        out = _copy_path(path)
        if not _private(out.parent, make=True):
            log.warning("🔧 Repaired copies folder is not this user's own\n"
                        "folder: %s", out.parent)
            return None
        if out.exists():
            return _reuse(out)
        data = path.read_bytes()
        start = first_frame(data, tag_size(data))
        if start is None:
            return None
        frame = frame_at(data, start)
        if frame is None:
            return None
        size, marker = frame
        info = bytearray(size)
        info[:4] = data[start:start + 4]
        info[1] |= 1                       # no CRC: the marker sits where it is counted
        info[marker:marker + 4] = b"Info"
        # A .part of its own: two instances repairing the same file must not
        # write into one. Still ends in .part, so prune_copies finds a crash's.
        fd, name = tempfile.mkstemp(dir=out.parent, prefix=out.stem + ".", suffix=".part")
        part = Path(name)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(bytes(info) + data[start:])
            part.replace(out)
        except OSError:
            part.unlink(missing_ok=True)
            if out.exists():               # the other instance got there first
                return _reuse(out)
            raise
        return out
    except OSError as e:
        log.warning("🔧 Could not make a repaired copy\n"
                    "file: %s\n"
                    "error: %s", path.name, e)
        return None
