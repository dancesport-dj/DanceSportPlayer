"""Make the recorded announcement voice easier to understand in a hall.

Marcel hears the male clips as clearer than the female ones, so the fix is to
treat the recordings rather than swap the voice. A hall PA, a floor full of
people and a room's reverb all eat the consonants first — what survives is the
fundamental, which is why an untreated voice reads as "warm but mumbled" over a
tournament system. The chain below cuts the rumble, takes a little out of the
mud the room adds anyway, lifts the presence band the consonants live in, and
evens the level so a quiet word doesn't disappear under the applause.

The EQ is BAKED IN rather than applied at playback: QMediaPlayer has no
equalizer, and ffmpeg is already a dependency of the announcement path (the
trim probe in player/announce.py runs it). The clips are static, so treating
them once costs nothing at run time.

Nothing is destroyed. The first --apply puts every untouched recording in
speech/announcements/<language>/<voice>/original/, and every run afterwards
reads from THERE,
not from the file it wrote last time — so running this twice cannot stack two
EQs on top of each other, and --restore always has somewhere to come back
from. What was baked in is written down beside the clips in eq_applied.md, so
the preset a recording carries never has to be guessed at by ear.

Listen before you bake. The values are speech-intelligibility practice, not
something anybody heard these clips through:

    .venv\\Scripts\\python.exe -m tools.announce_eq --audition
    .venv\\Scripts\\python.exe -m tools.announce_eq --audition --preset bright
    .venv\\Scripts\\python.exe -m tools.announce_eq --audition SB CCC WCS
    .venv\\Scripts\\python.exe -m tools.announce_eq --apply --voice female
    .venv\\Scripts\\python.exe -m tools.announce_eq --restore
    .venv\\Scripts\\python.exe -m tools.announce_eq --apply --language english
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from shared.audio_probes import find_ffmpeg
from player import announce

# Where the untouched recordings are kept, inside each voice's folder. A plain
# subfolder and not a sibling: `announce_clips` globs *.mp3 in the voice folder
# itself, so nothing here is ever mistaken for a clip to play.
ORIGINAL_DIR = "original"

# The record of what was baked in, written beside the clips it describes.
# Without it the only way to tell which preset a recording carries is to listen
# to it. Written by --apply, taken away by --restore, so it can never outlive
# the thing it describes.
NOTE_NAME = "eq_applied.md"

# The filter chains, in ffmpeg -af syntax.
#
# `clear` is the default and the one the reasoning above describes:
#   highpass 110 Hz   nothing a speaking voice does lives below this; it is
#                     mains hum, desk thumps and the PA's own rumble
#   -3 dB @ 300 Hz    the boxiness a room adds. Gentle and wide: her
#                     fundamental sits around 200 Hz and must not be thinned
#   +5 dB @ 3.2 kHz   presence — where t, k, s and the ends of words live,
#                     and the first thing a hall swallows
#   acompressor       evens the words out so a quiet one still carries
#   alimiter          catches what the makeup gain would otherwise clip
#
# `bright` is `clear` pushed further, with a de-esser to pay for it — try it
# when the presence lift still isn't enough; `warm` is for when `clear` turns
# her thin or sibilant. `off` bakes nothing and is there for an A/B.
PRESETS = {
    "clear": [
        "highpass=f=110",
        "equalizer=f=300:t=q:w=1.2:g=-3",
        "equalizer=f=3200:t=q:w=1.0:g=5",
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=3",
        "alimiter=limit=0.95",
    ],
    "bright": [
        "highpass=f=120",
        "equalizer=f=300:t=q:w=1.2:g=-4",
        "equalizer=f=3500:t=q:w=1.0:g=7",
        "deesser=i=0.4",
        "acompressor=threshold=-18dB:ratio=3:attack=5:release=120:makeup=3",
        "alimiter=limit=0.95",
    ],
    "warm": [
        "highpass=f=100",
        "equalizer=f=300:t=q:w=1.0:g=-2",
        "equalizer=f=3000:t=q:w=1.2:g=3",
        "acompressor=threshold=-20dB:ratio=2.5:attack=5:release=150:makeup=2",
        "alimiter=limit=0.95",
    ],
    "off": [],
}
DEFAULT_PRESET = "clear"

# The clips are mono 44.1 kHz at ~128 kbps; encoding back above that keeps the
# re-encode from being the thing anybody hears.
ENCODE = ["-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100", "-ac", "1"]

# What an audition plays when no words were named: the lead-in, then a word
# with a hard consonant, one that is all sibilance, and the longest one there
# is. Missing ones are skipped — a voice does not have to have them all.
AUDITION_CLIPS = ("next_dance", "QS", "SB", "WCS")


def chain(preset: str) -> str:
    """One preset as an ffmpeg -af argument ("" when it filters nothing)."""
    return ",".join(PRESETS[preset])


def voice_dirs(root: Path, voice: str) -> list[Path]:
    """The voice folders to work on — one of them, or every one installed."""
    names = announce._CLIP_GENDERS if voice == "both" else (voice,)
    return [root / n for n in names if (root / n).is_dir()]


def clips_of(folder: Path) -> list[Path]:
    """The clips of one voice. Not recursive, so the masters stay out of it."""
    return sorted(folder.glob("*.mp3"))


def master_of(clip: Path) -> Path:
    """The untouched recording behind a clip — what every run reads from."""
    return clip.parent / ORIGINAL_DIR / clip.name


def rerecorded(clip: Path) -> bool:
    """Whether the clip was written after the last --apply of its voice.

    Every clip that run treated is older than the note it wrote afterwards, so a
    newer clip is not the tool's work: the speech script recorded it again,
    straight over the file. Without a note nothing proves that, so the answer
    is no — the master stays the one to trust.
    """
    note = clip.parent / NOTE_NAME
    try:
        return clip.stat().st_mtime_ns > note.stat().st_mtime_ns
    except FileNotFoundError:
        return False


def keep_master(clip: Path) -> Path:
    """Put the recording aside the first time it is treated, and hand back the
    file to read. A master that is already there is only replaced by a clip
    recorded again since the last --apply: otherwise that copy is the only
    untreated one left."""
    master = master_of(clip)
    if not master.exists() or rerecorded(clip):
        master.parent.mkdir(exist_ok=True)
        shutil.copy2(clip, master)
    return master


def render(ffmpeg: str, src: Path, dst: Path, filters: str) -> tuple:
    """Run one clip through the chain. (ok, what ffmpeg said if it wasn't)."""
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(src)]
    if filters:
        cmd += ["-af", filters]
    # The format is named, not read off dst: the scratch file must not end in .mp3.
    cmd += ENCODE + ["-f", "mp3", str(dst)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          errors="replace", creationflags=flags)
    return proc.returncode == 0, (proc.stderr or "").strip()


def write_note(folder: Path, preset: str, done: int) -> Path:
    """Write down what this voice now carries, over any older note."""
    note = folder / NOTE_NAME
    lines = [f"# {folder.name}: announcement clips with an EQ baked in", "",
             f"- Preset: **{preset}**",
             f"- Applied: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
             f"- Clips treated: {done}",
             f"- The untouched recordings are in `{ORIGINAL_DIR}/`, and every run "
             "reads from there — applying again cannot stack a second EQ.",
             "", "## Filter chain (ffmpeg -af)", ""]
    lines += [f"    {f}" for f in PRESETS[preset]] or ["    (nothing)"]
    lines += ["", "## Re-encoded as", "", "    " + " ".join(ENCODE),
              "", "## To undo", "",
              "    .venv\\Scripts\\python.exe -m tools.announce_eq --restore", "",
              "Written by `tools/announce_eq.py`; the next --apply overwrites it.",
              ""]
    note.write_text("\n".join(lines), encoding="utf-8")
    return note


def apply_voice(ffmpeg: str, folder: Path, preset: str) -> tuple:
    """Bake a preset into every clip of one voice. (treated, failed)."""
    filters = chain(preset)
    done = failed = 0
    for clip in clips_of(folder):
        master = keep_master(clip)
        # Not *.mp3: a scratch file an interrupted run leaves behind would be
        # played as a clip, and treated as one next time.
        tmp = clip.with_name(clip.name + ".eq-tmp")
        try:
            ok, err = render(ffmpeg, master, tmp, filters)
            if not ok:
                print(f"   x {clip.name}: {err.splitlines()[-1] if err else 'ffmpeg failed'}")
                failed += 1
                continue
            tmp.replace(clip)
            done += 1
        finally:
            tmp.unlink(missing_ok=True)
    if done:
        write_note(folder, preset, done)
    return done, failed


def restore_voice(folder: Path) -> int:
    """Put the untouched recordings back. Returns how many came back."""
    masters = folder / ORIGINAL_DIR
    if not masters.is_dir():
        return 0
    back = 0
    for master in sorted(masters.glob("*.mp3")):
        clip = folder / master.name
        if rerecorded(clip):
            # Nothing baked into this one; the old master is the stale copy.
            shutil.copy2(clip, master)
        else:
            shutil.copy2(master, clip)
        back += 1
    (folder / NOTE_NAME).unlink(missing_ok=True)
    return back


def play(ffplay: str, path: Path):
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.run([ffplay, "-nodisp", "-autoexit", "-loglevel", "quiet",
                    str(path)], creationflags=flags)


def audition(ffmpeg: str, ffplay: str, folder: Path, filters: str,
             words) -> int:
    """Play each word as it is, then through the chain. Touches no clip."""
    picked = [folder / f"{w}.mp3" for w in words]
    picked = [p for p in picked if p.is_file()]
    if not picked:
        print(f"   none of {', '.join(words)} is recorded for {folder.name}")
        return 0
    with tempfile.TemporaryDirectory(prefix="dp_eq_") as tmp:
        for src in picked:
            # The master when there is one: auditioning a clip that was already
            # baked would be judging the chain on top of itself.
            heard = master_of(src) if master_of(src).exists() else src
            treated = Path(tmp) / src.name
            ok, err = render(ffmpeg, heard, treated, filters)
            if not ok:
                print(f"   x {src.stem}: {err.splitlines()[-1] if err else 'ffmpeg failed'}")
                continue
            print(f"   {src.stem}:  as recorded …", flush=True)
            play(ffplay, heard)
            print(f"   {src.stem}:  through the chain …", flush=True)
            play(ffplay, treated)
    return len(picked)


def main():
    # The console is cp1252 and the clip names print under a heading of box
    # characters — without this the tool dies on its own output.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words", nargs="*",
                    help="clip stems to audition (default: "
                         f"{', '.join(AUDITION_CLIPS)})")
    ap.add_argument("--preset", default=DEFAULT_PRESET, choices=sorted(PRESETS),
                    help=f"which chain to use (default: {DEFAULT_PRESET})")
    ap.add_argument("--voice", default="both",
                    choices=sorted(announce._CLIP_GENDERS) + ["both"],
                    help="which recorded voice to work on")
    ap.add_argument("--language", default=announce._CLIP_FALLBACK,
                    help="which language's clips (a folder under "
                         f"{announce._CLIP_DIR.name}/, default: "
                         f"{announce._CLIP_FALLBACK})")
    ap.add_argument("--audition", action="store_true",
                    help="listen to the chain, as recorded against treated; "
                         "changes nothing on disk")
    ap.add_argument("--apply", action="store_true",
                    help="bake the chain into the clips (the untouched "
                         f"recordings go to {ORIGINAL_DIR}/)")
    ap.add_argument("--restore", action="store_true",
                    help=f"put the {ORIGINAL_DIR}/ recordings back")
    args = ap.parse_args()

    root = announce._CLIP_DIR / args.language
    folders = voice_dirs(root, args.voice)
    if not folders:
        print(f"no recorded voice under {root}")
        return 1

    if args.restore:
        for folder in folders:
            back = restore_voice(folder)
            print(f"{folder.name}: {back} clips restored"
                  if back else
                  f"{folder.name}: nothing to restore — never treated")
        return 0

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("no ffmpeg — nothing to filter with")
        return 1
    filters = chain(args.preset)
    print(f"preset {args.preset}:  {filters or '(nothing)'}")

    if args.apply:
        for folder in folders:
            done, failed = apply_voice(ffmpeg, folder, args.preset)
            print(f"{folder.name}: {done} clips treated"
                  + (f", {failed} failed" if failed else "")
                  + (f", written down in {NOTE_NAME}" if done else ""))
        print(f"Run --restore to undo, or --apply again with another preset — "
              f"every run reads from {ORIGINAL_DIR}/, never from its own work.")
        return 0

    if not args.audition:
        ap.print_usage()
        print("\nNothing to do — ask for --audition, --apply or --restore.")
        return 1

    ffplay = str(Path(ffmpeg).with_name(Path(ffmpeg).stem.replace(
        "ffmpeg", "ffplay") + Path(ffmpeg).suffix))
    if not Path(ffplay).is_file():
        print(f"no ffplay beside ffmpeg ({ffplay}) — cannot audition")
        return 1
    words = args.words or list(AUDITION_CLIPS)
    for folder in folders:
        print(f"\n── {folder.name} ──")
        audition(ffmpeg, ffplay, folder, filters, words)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
