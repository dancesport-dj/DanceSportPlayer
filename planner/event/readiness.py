"""🚦 Is tonight ready? The pre-flight before an event.

Every check below already exists on its own: the red ❗ of a missing file and
the 🧭 path fixer, the 📊 loudness pass the 🔊 equalizer needs, the 🔇 silence
probe, the 🐂 Paso Doble highlights, 🔁 Check duplicates and 🎵 Check music.
Before an event the DJ has to remember all six. This runs them together over what will be
played (the decks and the Eintanzen list) and grades each one green, yellow or
red, with the action that fixes it.

Pure — no Qt; the cache is anything with the AudioCache getters — so the
grading is testable on hand-built track lists, the way planner/playlist/checks.py is.
"""

import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from planner import i18n
from planner.models import ALLOW_REPEAT
from planner.music.paths import PathRemapper

OK, WARN, FAIL = 0, 1, 2

# How many file names a red "missing" line lists before it says "…".
_NAMES_SHOWN = 3


@dataclass(frozen=True)
class Finding:
    key: str            # files / loudness / silences / pd / duplicates / music / empty
    level: int          # OK, WARN or FAIL
    title: str
    detail: str = ""
    count: int = 0
    fix: str | None = None   # the action behind the report's "Fix" link


def overall(findings: list[Finding]) -> int:
    """The light of the whole report: its worst line."""
    return max((f.level for f in findings), default=OK)


def _listed(names: list[str]) -> str:
    shown = ", ".join(names[:_NAMES_SHOWN])
    return shown + (", …" if len(names) > _NAMES_SHOWN else "")


def _names(paths: list[Path]) -> str:
    return _listed([p.stem for p in paths])


def _off_reference(present: Sequence[Path], root: str) -> tuple[int, list[Path]]:
    """Present titles that are not on the Referenzpfad, the way 🧭 Fix paths
    counts them: (how many have a copy there, the ones without)."""
    if not root.strip():
        return 0, []
    remapper = PathRemapper([root])
    copies, none = 0, []
    for p in present:
        hit = remapper.remap(p)
        if hit is None:
            none.append(p)
        elif str(hit).lower() != str(p).lower():
            copies += 1
    return copies, none


def _missing_finding(missing: list[Path], present: Sequence[Path] = (),
                     reference_root: str = "") -> Finding:
    title = i18n.t("📁  Music files")
    if not missing:
        copies, none = _off_reference(present, reference_root)
        if not copies and not none:
            return Finding("files", OK, title, i18n.t("Every title is where the list says."))
        # They play, but a bundle or another PC looks for them on the Referenzpfad.
        lines = [i18n.t("Every title is where the list says."),
                 i18n.t("%d titles are not on the Reference path.") % (copies + len(none))]
        if copies:
            lines.append(i18n.t("%d have a copy there — 🧭 Fix paths swaps them in.")
                         % copies)
        if none:
            lines.append(i18n.t("%d have no copy there: %s") % (len(none), _names(none)))
        return Finding("files", WARN, title, "\n".join(lines), copies + len(none), "paths")
    # A whole drive that is gone is one cause, not a hundred broken titles.
    drives = sorted({p.anchor for p in missing if p.anchor and not os.path.exists(p.anchor)})
    if drives:
        detail = (i18n.t("Drive %s is not connected — %d titles live there.")
                  % (", ".join(drives), len(missing)))
    else:
        detail = i18n.t("%d titles not found: %s") % (len(missing), _names(missing))
    return Finding("files", FAIL, title, detail, len(missing), "paths")


def _measure_finding(key: str, title: str, todo: list[Path], total: int,
                     done_text: str, todo_text: str, fix: str) -> Finding:
    if not todo:
        return Finding(key, OK, title, done_text)
    return Finding(key, WARN, title,
                   todo_text % (len(todo), total) + "\n" + _names(todo),
                   len(todo), fix)


def _dup_count(report: dict) -> int:
    within = sum(len(w.get("clusters") or ()) for w in report.get("within") or ())
    cross = sum(len(c.get("exact") or ()) + len(c.get("similar") or ())
                for c in report.get("cross") or ())
    return within + cross


def _music_finding(music: tuple) -> Finding:
    titles, playlists = music
    title = i18n.t("🎵  Music check")
    if not titles and not playlists:
        return Finding("music", OK, title,
                       i18n.t("No tempo, length or round-structure problem in the decks."))
    lines = []
    if titles:
        lines.append(i18n.t("%d titles with a tempo or length problem: %s")
                     % (len(titles), _listed(titles)))
    if playlists:
        lines.append(i18n.t("%d playlists with uneven rounds or heats: %s")
                     % (len(playlists), _listed(playlists)))
    return Finding("music", WARN, title, "\n".join(lines),
                   len(titles) + len(playlists), "music")


# What each output source is called in the 🔈 line — the captions of its
# picker in ⚙ Settings (shared.audio.playback.OUTPUT_SOURCES + 🎧).
_SOURCE_NAMES = {"music": "🎵  Music:",
                 "cartwall": "🎛  Cartwall:", "announcer": "🔈  Announcements:",
                 "cue": "🎧  Pre-listen:"}


def outputs_finding(unplugged: list[tuple[str, str]], cue_on_music: bool,
                    cue_shared: bool = False) -> Finding:
    """🔈 The chosen sound outputs: `unplugged` is (source, card name) per chosen
    card that is not plugged in, `cue_on_music` whether a 🎧 preview would be
    refused for landing on the music's output, `cue_shared` whether previews
    play there because no pre-listen output is chosen. A missing card for
    anything the hall hears is red — it plays on the system default instead; a
    missing pre-listen card is yellow, as is a preview that would be refused or
    heard in the hall."""
    title = i18n.t("🔈  Sound outputs")
    lines, level = [], OK
    for source, name in unplugged:
        lines.append(i18n.t("%s %s is not connected — it plays on the system default.")
                     % (i18n.t(_SOURCE_NAMES.get(source, source)), name))
        level = max(level, WARN if source == "cue" else FAIL)
    if cue_on_music:
        lines.append(i18n.t("🎧 Pre-listen is on the music's own output — every "
                            "preview is refused."))
        level = max(level, WARN)
    if cue_shared:
        lines.append(i18n.t("🎧 Pre-listen is on the same output as the music — the hall hears every preview."))
        level = max(level, WARN)
    if level == OK:
        return Finding("outputs", OK, title, i18n.t("Every chosen output is plugged in."))
    return Finding("outputs", level, title, "\n".join(lines), len(lines), "outputs")


def controller_finding(device: str, connected: bool) -> Finding | None:
    """🎛 The hardware controller, never red: not every evening needs one.
    None (no line) while none is set up."""
    if not device:
        return None
    title = i18n.t("🎛  Controller")
    if connected:
        return Finding("controller", OK, title, i18n.t("%s is connected.") % device)
    return Finding("controller", WARN, title,
                   i18n.t("%s is not connected — plug it in if tonight needs it.")
                   % device, 1, "controller")


def awake_finding(keep_awake: bool) -> Finding:
    """☀ Whether the app holds the screen and sleep off while music plays or
    the presenter screen is up."""
    title = i18n.t("☀  Screen and sleep")
    if keep_awake:
        return Finding("awake", OK, title,
                       i18n.t("While music plays or the presenter screen is up, the "
                              "screen, the beamer and the computer stay awake."))
    return Finding("awake", WARN, title,
                   i18n.t("☀ Keep the screen awake is off — an hour nobody touches "
                          "the desk blanks the screen and the beamer, and may put "
                          "the computer to sleep."), 1, "awake")


def readiness_findings(tracks: list[tuple], cache, dup_report: dict,
                       music: tuple | None = None,
                       reference_root: str = "") -> list[Finding]:
    """Grade `tracks` — (path, dance) pairs of everything that will be played,
    in any order and with repeats — for the event.

    `cache` answers get_lufs / get_silences / get_pd_highlights (None: no
    measurements are known, so those lines are left out). `dup_report` is
    the within/cross report of 🔁 Check duplicates. `music` is what 🎵 Check
    music found — (titles with a problem, playlists with a structure note) —
    or None when it did not run, which leaves its line out. With a
    `reference_root`, present titles off that Referenzpfad turn the files
    line yellow."""
    seen: dict[str, tuple[Path, str]] = {}
    for path, dance in tracks:
        seen.setdefault(str(path), (Path(path), dance or ""))
    if not seen:
        return [Finding("empty", WARN, i18n.t("🎶  Playlists"),
                        i18n.t("Nothing to play yet — load or build a playlist first."))]

    present: list[tuple[Path, str]] = []
    missing: list[tuple[Path, str]] = []
    for path, dance in seen.values():
        (present if path.exists() else missing).append((path, dance))
    findings = [_missing_finding([p for p, _d in missing], [p for p, _d in present],
                                 reference_root)]

    if cache is not None:
        # A missing file cannot be measured: it is already the red line above.
        findings.append(_measure_finding(
            "loudness", i18n.t("📊  Loudness"),
            [p for p, _d in present if cache.get_lufs(p, touch_disk=False) is None],
            len(present),
            i18n.t("Every title is measured — 🔊 Equalize volume can stay on."),
            i18n.t("%d of %d titles have no loudness measurement — "
                   "🔊 Equalize volume stays off."),
            "loudness"))
        findings.append(_measure_finding(
            "silences", i18n.t("🔇  Silence probe"),
            [p for p, _d in present if cache.get_silences(p, touch_disk=False) is None],
            len(present),
            i18n.t("Every title is probed — playback skips its silent edges."),
            i18n.t("%d of %d titles are not probed — each is decoded when it starts."),
            "silences"))
        pasos = [p for p, d in present if d in ALLOW_REPEAT]
        findings.append(_measure_finding(
            "pd", i18n.t("🐂  Paso Doble highlights"),
            [p for p in pasos if cache.get_pd_highlights(p) is None],
            len(pasos),
            (i18n.t("Every Paso Doble knows its highlights.") if pasos
             else i18n.t("No Paso Doble in tonight's lists.")),
            i18n.t("%d of %d Paso Dobles have no highlights — 🐂 cannot stop at one."),
            "pd"))

    n = _dup_count(dup_report or {})
    findings.append(
        Finding("duplicates", WARN, i18n.t("🔁  Duplicates"),
                i18n.t("%d duplicates across the decks and the Practice list.") % n,
                n, "duplicates") if n else
        Finding("duplicates", OK, i18n.t("🔁  Duplicates"),
                i18n.t("No title is planned twice.")))
    if music is not None:
        findings.append(_music_finding(music))
    return findings
