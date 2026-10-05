#!/usr/bin/env python3
"""Cut a short snippet out of every file in a folder whose name contains "LW".

Stream-copies the first N seconds (no re-encode) into a `snippets/` subfolder,
at most 25 files per run.
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("lw_snippets")

# Same bundled-ffmpeg locations the GUI uses (see find_ffmpeg in shared/audio_probes.py).
_FFMPEG_CANDIDATES = (
    Path(__file__).parents[1] / "ffmpeg.exe",
    Path(__file__).parents[1] / "ffmpeg-9.0.2-essentials_build" / "bin" / "ffmpeg.exe",
)


def find_ffmpeg() -> str | None:
    """ffmpeg on PATH, else the copy bundled with the project, else the one
    shipped inside imageio_ffmpeg (installed in the venv), else None."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    for cand in _FFMPEG_CANDIDATES:
        if cand.is_file():
            return str(cand)
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def cut_snippet(ffmpeg: str, src: Path, dst: Path, start: float, duration: float):
    """Copy `duration` seconds starting at `start` from src to dst.

    Returns (ok, stderr). `-c copy` means no re-encode, so with a non-zero start
    the cut snaps to the nearest keyframe."""
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
         "-ss", str(start), "-i", str(src), "-t", str(duration),
         "-c", "copy", str(dst)],
        capture_output=True, text=True, errors="replace", creationflags=flags)
    return proc.returncode == 0, (proc.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="folder to read the files from")
    ap.add_argument("-o", "--out-dir", type=Path, help="default: <path>/snippets")
    ap.add_argument("-s", "--start", type=float, default=0.0, help="snippet start in seconds")
    ap.add_argument("-d", "--duration", type=float, default=8.0, help="snippet length in seconds")
    ap.add_argument("-l", "--limit", type=int, default=100, help="max number of files")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.path.is_dir():
        log.error("📁 Not a folder: %s", args.path)
        return 1

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        log.error("🎬 ffmpeg not found\n"
                  "looked in: PATH, project folder, imageio_ffmpeg")
        return 1

    files = sorted(f for f in args.path.iterdir() if f.is_file() and "LW" in f.name)
    files = files[:args.limit]
    if not files:
        log.info("🔍 No files containing 'LW'\n"
                 "path: %s", args.path)
        return 0

    out_dir = args.out_dir or args.path / "snippets"
    out_dir.mkdir(parents=True, exist_ok=True)

    done = 0
    for f in files:
        ok, err = cut_snippet(ffmpeg, f, out_dir / f"{f.stem}_snippet{f.suffix}",
                              args.start, args.duration)
        if ok:
            done += 1
            log.info("✂️ %s", f.name)
        else:
            log.warning("⚠️ Cut failed\n"
                        "file: %s\n"
                        "error: %s", f.name, err)

    log.info("✅ Done\n"
             "snippets: %d\n"
             "output: %s", done, out_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
