#!/usr/bin/env python3
"""Cut a short snippet out of every file in a folder whose name contains "LW".

Stream-copies the first N seconds (no re-encode) into a `snippets/` subfolder,
at most 100 files per run (--limit).
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# The GUI's lookup: it never runs an ffmpeg.exe planted in the current (music) folder.
from shared.audio.audio_probes import find_ffmpeg

log = logging.getLogger("lw_snippets")


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
                  "looked in: project folder, PATH")
        return 1

    files = sorted(f for f in args.path.iterdir() if f.is_file() and "LW" in f.name
                   and not f.stem.endswith("_snippet"))
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
    return 0 if done else 1


if __name__ == "__main__":
    sys.exit(main())
