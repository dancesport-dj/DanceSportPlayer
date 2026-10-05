"""Interactive command-line entry point for the planner.

Extracted from dancesport_planner.py (logical split): the text menus/prompts,
the playlist display and refine loop and main(). The GUI does not use this.
"""
import logging

import re
import sys
from planner.db import (  # auto-resolved
    AudioCache,
)
from planner.models import (  # auto-resolved
    ALLOW_REPEAT,
    DANCE_NAMES,
    DANCE_STYLES,
    DEFAULT_DANCES,
    Playlist,
    ROUND_NAMES,
    RoundConfig,
)
from planner.parsing import (  # auto-resolved
    _fmt_bpm,
)
from planner.scoring import (  # auto-resolved
    STRATEGIES,
    STRATEGY_HELP,
    STRATEGY_LABELS,
    _resolve_strategy,
)
from planner.library import (  # auto-resolved
    MusicLibrary,
)
from planner.suggester import (  # auto-resolved
    PlaylistSuggester,
)
from planner.m3u import (  # auto-resolved
    export_m3u,
)

log = logging.getLogger("dancesport.cli")


# ── CLI Helpers ────────────────────────────────────────────────────────────────
LINE  = "─" * 64


DLINE = "═" * 64


def hdr(title: str) -> None:
    print(f"\n{DLINE}\n  {title}\n{DLINE}")


def sep(label: str = "") -> None:
    if label:
        pad = max(0, 64 - len(label) - 4)
        print(f"── {label} " + "─" * pad)
    else:
        print(LINE)


def ask_choice(prompt: str, options: list[str], default: str | None = None) -> str:
    print(f"\n{prompt}")
    for i, o in enumerate(options, 1):
        marker = "  ← default" if o == default else ""
        print(f"  {i}. {o}{marker}")
    while True:
        raw = input("  Choice: ").strip()
        if not raw and default:
            return default
        upper = [o.upper() for o in options]
        if raw.upper() in upper:
            return options[upper.index(raw.upper())]
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        print(f"  Please enter 1–{len(options)} or the option text.")


def ask_dances(style: str, default: list[str]) -> list[str]:
    all_d = list(DEFAULT_DANCES[style]['S'])
    print(f"\n  Dance selection: {', '.join(DANCE_NAMES[d] for d in default)}")
    if input("  Modify? [y/N]: ").strip().lower() != 'y':
        return default
    print("  Available:")
    for i, d in enumerate(all_d, 1):
        print(f"    {i}. {DANCE_NAMES[d]}")
    while True:
        raw = input("  Numbers (comma-separated, e.g. 1,2,4): ").strip()
        try:
            chosen = [all_d[int(x)-1] for x in raw.split(',') if x.strip()]
            if chosen:
                return chosen
        except (ValueError, IndexError):
            pass
        print("  Invalid, try again.")


def ask_rounds_with_heats() -> list[RoundConfig]:
    print()
    print("  Enter heats per round, first round → last round (Finale).")
    print("  Format: numbers separated by dash or space.")
    print("  Example:  6-3-2-1  means 4 rounds with 6 / 3 / 2 / 1 heats.")
    print("  Each number = how many different songs are needed per dance in that round.")
    while True:
        raw = input("\n  Heats per round: ").strip()
        parts = re.split(r'[-,\s]+', raw)
        try:
            counts = [int(p) for p in parts if p]
            if counts and all(1 <= c <= 30 for c in counts):
                break
        except ValueError:
            pass
        print("  Please enter positive integers, e.g.  6-3-2-1")

    n     = len(counts)
    names = ROUND_NAMES.get(n, [f"Runde {i+1}" for i in range(n)])
    cfgs  = []
    for i, (name, heats) in enumerate(zip(names, counts)):
        tier = (
            'final'    if i == n - 1       else
            'semi'     if i == n - 2       else
            'pre_semi' if i == n - 3       else
            'early'
        )
        # Default strategy: pre_semi prefers fresh; everything else prefers proven
        prefer_fresh = (tier == 'pre_semi')
        cfgs.append(RoundConfig(name=name, heats=heats, tier=tier,
                                prefer_fresh=prefer_fresh))

    print("\n  Round plan:")
    for rc in cfgs:
        print(f"    {rc.name:<22} {rc.heats} heat(s)  [{rc.tier}]")

    # Ask the song-pool strategy for every round (each defaults to its tier's natural choice)
    _num_to_strat = {str(i + 1): s for i, s in enumerate(STRATEGIES)}
    print("\n  Song pool per round:")
    print("    " + "  ".join(f"{n}={STRATEGY_LABELS[s]}" for n, s in _num_to_strat.items()))
    for s in STRATEGIES:
        print(f"      • {STRATEGY_LABELS[s]}: {STRATEGY_HELP[s]}")
    for rc in cfgs:
        default = _resolve_strategy(rc.tier, rc.prefer_fresh, rc.strategy or None)
        default_num = {v: k for k, v in _num_to_strat.items()}[default]
        raw = input(
            f"    {rc.name:<22}  [{default_num}={STRATEGY_LABELS[default]}]: ").strip()
        if raw in _num_to_strat:
            rc.strategy = _num_to_strat[raw]
        else:
            rc.strategy = default   # lock in the resolved default explicitly

    return cfgs


# ── Display ────────────────────────────────────────────────────────────────────
def _round_label(rc: RoundConfig) -> str:
    strat = _resolve_strategy(rc.tier, rc.prefer_fresh, rc.strategy or None)
    return f'  [→ {STRATEGY_LABELS[strat].lower()} songs]'


def display_playlist(playlist: Playlist, dances: list[str],
                     rounds: list[RoundConfig], dance_class: str = "C") -> None:
    rc_map = {rc.name: rc for rc in rounds}

    for round_name, heats in playlist.items():
        rc    = rc_map.get(round_name)
        tier  = rc.tier if rc else 'early'
        total = sum(1 for h in heats for e in h if e is not None)
        sep()
        label = _round_label(rc) if rc else ''
        print(f"  {round_name.upper()}  ({len(heats)} heat(s), {total} songs){label}")
        sep()

        multi = len(heats) > 1
        for d_idx, dance in enumerate(dances):
            dn = DANCE_NAMES.get(dance, dance)
            print(f"  {dn}:")
            for h_idx, heat in enumerate(heats, 1):
                entry  = heat[d_idx]
                prefix = f"    Heat {h_idx}:  " if multi else "    "
                if entry:
                    bpm_s  = _fmt_bpm(entry.bpm, dance, dance_class)
                    pop_s  = f" ★{entry.popularity}" if entry.popularity else "  ✦new"
                    src_s  = f"  ← {entry.source_info}" if entry.source_info and tier in ('semi','final') else ""
                    sim_s  = " ≈" if (entry.sim_score is not None and entry.sim_score >= 0.7) else ""
                    cls_s  = f" [{','.join(entry.classes_ok)}]" if entry.classes_ok else ""
                    title  = entry.title[:40]
                    print(f"{prefix}{title}{bpm_s}{pop_s}{sim_s}{cls_s}{src_s}")
                else:
                    print(f"{prefix}⚠  No suitable song found!")
            print()


# ── Interactive Refinement ─────────────────────────────────────────────────────
def interactive_refine(
    playlist: Playlist,
    dances: list[str],
    dance_class: str,
    rounds: list[RoundConfig],
    suggester: PlaylistSuggester,
) -> Playlist:
    tier_map = {rc.name: rc.tier for rc in rounds}

    while True:
        if input("Replace a song? [y/N]: ").strip().lower() != 'y':
            break

        round_labels = list(playlist.keys())
        print("\n  Rounds:")
        for i, r in enumerate(round_labels, 1):
            n_heats = len(playlist[r])
            print(f"    {i}. {r}  ({n_heats} heat(s))")

        r_raw = input("  Select round (number): ").strip()
        try:
            r_idx = int(r_raw) - 1
            if not (0 <= r_idx < len(round_labels)):
                raise ValueError
        except ValueError:
            print("  Invalid."); continue
        round_name = round_labels[r_idx]
        heats      = playlist[round_name]

        h_idx = 0
        if len(heats) > 1:
            h_raw = input(f"  Select heat (1–{len(heats)}): ").strip()
            try:
                h_idx = int(h_raw) - 1
                if not (0 <= h_idx < len(heats)):
                    raise ValueError
            except ValueError:
                print("  Invalid."); continue

        heat = heats[h_idx]
        print(f"\n  Songs in {round_name}, Heat {h_idx+1}:")
        for i, (dance, entry) in enumerate(zip(dances, heat), 1):
            dn    = DANCE_NAMES.get(dance, dance)
            title = entry.title[:40] if entry else "(none)"
            print(f"    {i}. {dn}: {title}")

        d_raw = input(f"  Select dance (1–{len(dances)}): ").strip()
        try:
            d_idx = int(d_raw) - 1
            if not (0 <= d_idx < len(dances)):
                raise ValueError
        except ValueError:
            print("  Invalid."); continue

        dance = dances[d_idx]
        tier  = tier_map.get(round_name, 'early')

        # Build full exclusion set (all currently used paths, minus current song)
        exclude = {
            str(e.path)
            for hs in playlist.values()
            for h  in hs
            for e  in h
            if e is not None
        }
        current = heat[d_idx]
        if current and dance not in ALLOW_REPEAT:
            exclude.discard(str(current.path))

        new_entry = suggester.regenerate(dance, dance_class, tier, exclude)
        if new_entry:
            heat[d_idx] = new_entry
            bpm_s = _fmt_bpm(new_entry.bpm, dance, dance_class)
            print(f"  Replaced with: {new_entry.title}{bpm_s}")
        else:
            print("  No alternative found.")

        print()
        display_playlist(playlist, dances, rounds, dance_class)

    return playlist


# ── Main ───────────────────────────────────────────────────────────────────────
def main() -> None:
    # Bare-message handler on stdout so log output blends with the CLI UI prints.
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    hdr("Dancesport Playlist Planner")

    # ── Audio cache + library ──
    print()
    cache = AudioCache()
    lib   = MusicLibrary()
    lib.scan(cache)

    # ── Library summary ──
    summary       = lib.summary()
    other_summary = lib.other_genre_summary()
    sep()
    print("  Competition dances:")
    for code in list(DANCE_NAMES.keys()):
        n = summary.get(code, 0)
        if n > 0:
            bar = '█' * min(n // 5, 30)
            print(f"  {DANCE_NAMES[code]:<22} {n:>4}  {bar}")
    if other_summary:
        print("\n  Other genres (not used for playlists):")
        for label, n in sorted(other_summary.items(), key=lambda x: -x[1]):
            bar = '█' * min(n // 5, 30)
            print(f"  {label:<22} {n:>4}  {bar}")
    untagged = summary.get('?', 0) - sum(other_summary.values())
    if untagged > 0:
        print(f"\n  No dance detected        {untagged:>4}")
    has_audio = sum(1 for e in lib.entries if e.features)
    if has_audio:
        print(f"\n  Audio features available: {has_audio}/{len(lib.entries)} files")
    sep()

    while True:
        hdr("Tournament Configuration")

        style      = ask_choice("Dance style:", list(DANCE_STYLES), default="Latin")
        age_group  = ask_choice("Age class:", [
            "Kinder", "Junioren", "Jugend",
            "Hauptgruppe", "Senioren I", "Senioren II", "Senioren III",
            "Senioren IV", "Senioren V",
        ], default="Hauptgruppe")
        dance_class = ask_choice("Start class:", ["D","C","B","A","S"], default="S")
        dances      = ask_dances(style, DEFAULT_DANCES[style][dance_class])
        rounds      = ask_rounds_with_heats()

        suggester   = PlaylistSuggester(lib)
        iteration   = 1

        while True:
            total_songs = sum(rc.heats for rc in rounds) * len(dances)
            print(f"\n  Generating playlist … "
                  f"{sum(rc.heats for rc in rounds)} heats × {len(dances)} dances"
                  f" = {total_songs} songs total"
                  + (f"  (iteration {iteration})" if iteration > 1 else ""))

            playlist = suggester.suggest(dance_class, rounds, dances, style=style)

            hdr(f"Suggested Playlist  ·  {age_group} {dance_class} {style}"
                + (f"  #{iteration}" if iteration > 1 else ""))
            display_playlist(playlist, dances, rounds, dance_class)

            playlist = interactive_refine(playlist, dances, dance_class, rounds, suggester)

            ans = input("Save as M3U file? [Y/n]: ").strip().lower()
            if ans != 'n':
                suffix   = f"_v{iteration}" if iteration > 1 else ""
                basename = f"{age_group.replace(' ','_')}_{dance_class}_{style}{suffix}"
                out = export_m3u(playlist, dances, basename, dance_class)
                print(f"  Saved: {out}")

            nxt = input("\nAnother iteration (same settings) [Y] / New config [c] / Quit [n]: ").strip().lower()
            if nxt == 'n':
                print("\nGood luck with your tournament!\n")
                return
            if nxt == 'c':
                break   # break inner loop → outer loop asks for new config
            iteration += 1  # re-run with same settings
