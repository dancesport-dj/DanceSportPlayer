#!/usr/bin/env python3
"""Tests for planner.warmup — the ETDS / 'Eintanzen' party-list builder.

Run:  py -m unittest tests.planner.test_warmup -v

Entries are built by hand under standardcd/lateincd paths. The builder is
random, so the round-shape tests seed `random` and check the same invariant
across several seeds rather than pinning one exact list.
"""

import random
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.warmup import (
    _WARMUP_BALLROOM,
    _WARMUP_LATIN,
    _WARMUP_MODE,
    _WARMUP_ORDER,
    _warmup_section_round,
    build_warmup_playlist,
    warmup_code,
    warmup_section,
)

# Always-on core dances: these must keep coming back regardless of the
# probability weights. WW and PD are deliberately NOT here — they stay
# probability-only until their warm-up gate (WW ≥ 12, PD ≥ 40 tracks).
_CORE_STD = ["LW", "TG", "SF", "QS"]
_CORE_LAT = ["SA", "CC", "RB", "JI"]

_STYLE_DIR = {d: ("lateincd" if d in _WARMUP_LATIN else "standardcd")
              for d in _WARMUP_BALLROOM + _WARMUP_LATIN}

_SEEDS = range(12)


def _entry(dance: str, i: int) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\{_STYLE_DIR.get(dance, 'others')}\{dance}\{dance}{i}.mp3"),
        title=f"{dance} {i}", dance=dance, duration=180)


def _social(code: str, i: int) -> MusicEntry:
    """A social track: no competition dance, genre label drives warmup_code."""
    label = {"DISCOFOX": "Discofox", "SALSA": "Salsa", "BACHATA": "Bachata",
             "WCS": "West Coast Swing", "KIZOMBA": "Kizomba", "FORRO": "Forró"}[code]
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\others\{code}\{code}{i}.mp3"),
        title=f"{label} {i}", dance=None, other_genre=label, duration=180)


def _pool(n=40, social=0) -> list:
    out = [_entry(d, i) for d in _WARMUP_BALLROOM + _WARMUP_LATIN
           for i in range(n)]
    out += [_social(c, i) for c in _WARMUP_MODE for i in range(social)]
    return out


def _section_codes(result, section) -> list:
    """The result's own dance codes, keeping only this section's tracks."""
    return [c for c in (warmup_code(e) for e in result) if c in section]


def _last_round(result) -> list:
    """The trailing run of tracks sharing one section label — the round the
    list ends on, as `warmup_section` groups them."""
    label = warmup_section(result[-1])
    out = []
    for e in reversed(result):
        if warmup_section(e) != label:
            break
        out.append(warmup_code(e))
    return list(reversed(out))


def _max_return_gap(codes, dance):
    """Largest number of the section's tracks between two appearances of
    `dance` (None when it appears less than twice)."""
    idx = [i for i, c in enumerate(codes) if c == dance]
    if len(idx) < 2:
        return None
    return max(b - a for a, b in zip(idx, idx[1:]))


class WarmupCoverageTest(unittest.TestCase):
    """The coverage guarantee: a core dance that hasn't shown up in the last two
    rounds is pulled into the next one, so no core dance can be starved out by
    its ETDS probability weight."""

    def test_core_dance_never_disappears_for_long(self):
        # Rounds hold three dances, and the overdue check looks back two rounds,
        # so a core dance returns within ~3 rounds. Rounds can be short when a
        # pool thins, which stretches the worst observed gap to 11 of the
        # section's tracks — 12 is the non-flaky bound (measured over 300 seeds).
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = build_warmup_playlist(_pool())
                for section, core in ((_WARMUP_BALLROOM, _CORE_STD),
                                      (_WARMUP_LATIN, _CORE_LAT)):
                    codes = _section_codes(res, section)
                    for d in core:
                        gap = _max_return_gap(codes, d)
                        self.assertIsNotNone(gap, f"{d} appeared at most once")
                        self.assertLessEqual(
                            gap, 12,
                            f"{d} went missing for {gap} tracks of its section")

    def test_overdue_dance_is_pulled_into_the_next_round(self):
        """SF absent from the last two Standard rounds → next round must take it,
        whatever the weights say."""
        pools = {d: [_entry(d, i) for i in range(20)]
                 for d in _WARMUP_BALLROOM}
        # Two rounds of LW/TG/QS: SF is the only core dance now overdue.
        result = [_entry(d, 90 + i)
                  for i in range(2) for d in ("LW", "TG", "QS")]
        history = [["LW", "TG", "QS"], ["LW", "TG", "QS"]]
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = list(result)
                took = _warmup_section_round(res, {d: list(v) for d, v in pools.items()},
                                             _WARMUP_BALLROOM,
                                             late_ww=True, late_pd=True,
                                             rounds=[list(r) for r in history],
                                             deferred=[])
                self.assertTrue(took)
                picked = [warmup_code(e) for e in res[len(result):]]
                self.assertIn("SF", picked)

    def test_first_round_opens_with_the_competition_order(self):
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = build_warmup_playlist(_pool())
                std = _section_codes(res, _WARMUP_BALLROOM)
                lat = _section_codes(res, _WARMUP_LATIN)
                self.assertEqual(std[:3], ["LW", "TG", "QS"])
                self.assertEqual(lat[:3], ["CC", "RB", "JI"])

    def test_late_gates_hold_back_ww_and_pd(self):
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = build_warmup_playlist(_pool(), late_ww=True, late_pd=True)
                codes = [warmup_code(e) for e in res]
                self.assertNotIn("WW", codes[:12])
                self.assertNotIn("PD", codes[:40])


class WarmupWienerWalzerTest(unittest.TestCase):
    """A Wiener Walzer must never be the title straight after a Langsamer
    Walzer inside a round: the floor goes from the slowest waltz to the fastest
    with nothing in between.

    The rule may only be honoured across the round boundary. Competition order
    inside a round is fixed — "i want the order to be fixed in copetition
    order. in this case where lw ww is shuffled put one of them into the next
    round" — so a round that draws both waltzes hands one of them on rather
    than rearranging itself around them.

    Read the rounds off the planner rather than off the finished list — the
    flat playlist has no round boundaries in it, and a LW ending one round
    ahead of a WW opening the next is a different (allowed) thing."""

    def _rounds(self, **kw):
        """Every Standard round the builder planned, in the order it plays."""
        import planner.warmup as w
        seen = []
        real = w._warmup_section_round

        def spy(result, pools, section, **kwargs):
            took = real(result, pools, section, **kwargs)
            if took and section is _WARMUP_BALLROOM:
                seen.append(list(kwargs["rounds"][-1]))
            return took

        w._warmup_section_round = spy
        try:
            build_warmup_playlist(_pool(), **kw)
        finally:
            w._warmup_section_round = real
        return seen

    def test_a_wiener_walzer_never_follows_a_langsamer_walzer_in_a_round(self):
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                for rnd in self._rounds(late_ww=False):
                    for a, b in zip(rnd, rnd[1:]):
                        self.assertFalse(
                            a == "LW" and b == "WW",
                            f"round {rnd} plays WW straight after LW")

    def test_every_round_keeps_competition_order(self):
        """The rule above must not be bought with a reordered round: whatever
        a round holds, it plays in LW TG WW SF QS order."""
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                for rnd in self._rounds(late_ww=False):
                    self.assertEqual(
                        rnd, sorted(rnd, key=lambda d: _WARMUP_ORDER.get(d, 99)),
                        f"round {rnd} is out of competition order")


class WarmupSectionOrderTest(unittest.TestCase):
    """The section cycle is fixed per pass (STD → LAT → STD → LAT …), not
    flipped every pass — flipping produced the wrong STD LAT | LAT STD run."""

    def test_sections_alternate_without_flipping(self):
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = build_warmup_playlist(_pool())
                sections = [warmup_section(e) for e in res[:12]]
                self.assertEqual(sections, ["Standardrunde"] * 3
                                 + ["Lateinrunde"] * 3
                                 + ["Standardrunde"] * 3
                                 + ["Lateinrunde"] * 3)

    def test_start_with_latin_swaps_the_two_sections(self):
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                random.seed(seed)
                res = build_warmup_playlist(_pool(), start_with_latin=True)
                sections = [warmup_section(e) for e in res[:6]]
                self.assertEqual(sections, ["Lateinrunde"] * 3
                                 + ["Standardrunde"] * 3)

    def test_warmup_section_labels_every_warmup_dance(self):
        for d in _WARMUP_BALLROOM:
            self.assertEqual(warmup_section(_entry(d, 0)), "Standardrunde")
        for d in _WARMUP_LATIN:
            self.assertEqual(warmup_section(_entry(d, 0)), "Lateinrunde")
        for c in _WARMUP_MODE:
            self.assertEqual(warmup_section(_social(c, 0)), "Socialrunde")
        self.assertIsNone(warmup_section(_entry("TANGOARG", 0)))

    def test_tango_argentino_by_its_genre_is_the_dance(self):
        """Labelled by its genre, as a social track is, it was no dance at
        all: a blank Dance cell, "other" in the Σ line, its German name on an
        English screen. It is a dance, yet still no warm-up section."""
        e = MusicEntry(path=Path(r"C:\music\others\ta.mp3"), title="Por una cabeza",
                       dance=None, other_genre="Tango Argentino", duration=180)
        self.assertEqual(warmup_code(e), "TANGOARG")
        self.assertIsNone(warmup_section(e))


class WarmupOptionsTest(unittest.TestCase):
    def test_max_tracks_caps_the_list(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(), max_tracks=50)
        self.assertEqual(len(res), 51)          # the round it lands in is played out

    def test_max_tracks_never_cuts_a_round_in_half(self):
        """"Max tracks" is a length the operator asked for, not a place to cut.
        A round that has started is played out, so the list may run a title or
        two past the cap rather than end on half a round — "i dont want a round
        run short"."""
        for cap in (50, 80, 100, 110, 200):
            with self.subTest(cap=cap):
                random.seed(0)
                res = build_warmup_playlist(_pool(n=60), include_modetaenze=True,
                                            max_tracks=cap)
                self.assertGreaterEqual(len(res), cap)
                self.assertLess(len(res), cap + 3)
                last = _last_round(res)
                if warmup_section(res[-1]) != "Socialrunde":
                    self.assertEqual(len(last), 3,
                                     f"cap {cap} ended on {last}")

    def test_no_max_tracks_uses_every_eligible_track(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(n=10))
        self.assertEqual(len(res), 100)         # 10 dances × 10 tracks
        self.assertEqual(len(set(id(e) for e in res)), 100)   # each used once

    def test_modetaenze_subset_restricts_the_social_dances(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(social=5), include_modetaenze=True,
                                    modetaenze=["DISCOFOX", "SALSA"])
        social = {c for c in (warmup_code(e) for e in res) if c in _WARMUP_MODE}
        self.assertTrue(social)
        self.assertLessEqual(social, {"DISCOFOX", "SALSA"})

    def test_the_first_social_track_of_a_party_list_is_a_discofox(self):
        """Whatever else the evening draws, the floor is opened with Discofox."""
        for seed in _SEEDS:
            random.seed(seed)
            res = build_warmup_playlist(_pool(social=5), include_modetaenze=True)
            social = [c for c in (warmup_code(e) for e in res)
                      if c in _WARMUP_MODE]
            self.assertTrue(social, f"seed {seed}")
            self.assertEqual(social[0], "DISCOFOX", f"seed {seed}")

    def test_an_unticked_discofox_does_not_open_the_social_rounds(self):
        # Discofox opens the first social round — but only when it was picked.
        for seed in _SEEDS:
            random.seed(seed)
            res = build_warmup_playlist(_pool(social=5), include_modetaenze=True,
                                        modetaenze=["SALSA", "BACHATA"])
            codes = {warmup_code(e) for e in res}
            self.assertNotIn("DISCOFOX", codes, f"seed {seed}")
            self.assertTrue(codes & {"SALSA", "BACHATA"}, f"seed {seed}")

    def test_modetaenze_off_drops_every_social_track(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(social=5), include_modetaenze=False)
        codes = {warmup_code(e) for e in res}
        self.assertFalse(codes & set(_WARMUP_MODE))

    def test_no_paso_drops_paso_doble(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(), no_paso=True)
        self.assertNotIn("PD", [warmup_code(e) for e in res])

    def test_single_section_only(self):
        random.seed(0)
        res = build_warmup_playlist(_pool(), include_latin=False)
        self.assertTrue(res)
        self.assertFalse({warmup_code(e) for e in res} & set(_WARMUP_LATIN))


class WarmupPasoSocialTest(unittest.TestCase):
    """A Paso Doble that closes its Latin round is never followed by two social
    titles in a row — the interlude behind it holds a single one."""

    def _party(self, seed):
        """One party list as dance codes. The social pool is deliberately the
        small one: it has to run dry BEFORE the competition sections do, or the
        list ends on one long block of leftover social titles and every rule
        about what follows what reads that block instead of a round."""
        random.seed(seed)
        return [warmup_code(e) for e in build_warmup_playlist(
            _pool(social=10), include_modetaenze=True, late_pd=False)]

    def _doubles_behind(self, codes, dance):
        """How many `dance` titles are followed by two social ones."""
        return sum(1 for i, c in enumerate(codes[:-2])
                   if c == dance and codes[i + 1] in _WARMUP_MODE
                   and codes[i + 2] in _WARMUP_MODE)

    def test_a_paso_is_never_followed_by_two_social_titles(self):
        touching = 0        # Pasos that open onto a social round at all
        for seed in _SEEDS:
            with self.subTest(seed=seed):
                codes = self._party(seed)
                for i, c in enumerate(codes[:-2]):
                    if c != "PD" or codes[i + 1] not in _WARMUP_MODE:
                        continue
                    touching += 1
                    self.assertNotIn(
                        codes[i + 2], _WARMUP_MODE,
                        f"seed {seed}: the Paso at {i} is followed by "
                        f"{codes[i + 1]} and {codes[i + 2]}")
        # Guard against a vacuous pass: the situation has to actually occur.
        self.assertGreaterEqual(touching, len(_SEEDS),
                                "no Paso ended a Latin round in the whole run")

    def test_the_social_rounds_still_come_in_pairs_elsewhere(self):
        """The rule shortens the interlude behind a Paso, not every interlude —
        a double social round is what fills the floor."""
        doubles = sum(self._doubles_behind(self._party(seed), "JI")
                      for seed in _SEEDS)
        self.assertTrue(doubles, "no double social round left anywhere")

    def test_a_jive_behind_the_paso_separates_it_from_the_socials(self):
        """A round is sorted SA CC RB PD JI, so a Paso drawn together with a
        Jive does not touch the interlude — and that one may still be a double.

        Scanned over more seeds than the invariant tests above: this one asks
        that a situation OCCURS, and it needs a Paso, a Jive and a doubled
        interlude to coincide. It comes out in roughly a third of seeds
        (measured: 72 of 200), so the usual twelve is a coin toss — the first
        twelve held an example until an unrelated change to the Standard
        section moved the draw."""
        seen = 0
        for seed in range(24):
            codes = self._party(seed)
            seen += sum(1 for i, c in enumerate(codes[:-3])
                        if c == "PD" and codes[i + 1] == "JI"
                        and codes[i + 2] in _WARMUP_MODE
                        and codes[i + 3] in _WARMUP_MODE)
        self.assertTrue(seen, "a Paso followed by a Jive never kept its double")


class WarmupProgressTest(unittest.TestCase):
    def test_progress_ends_at_the_real_length(self):
        seen = []
        random.seed(0)
        res = build_warmup_playlist(_pool(n=10),
                                    progress_cb=lambda d, t: seen.append((d, t)))
        self.assertEqual(seen[0], (0, 100))       # total known up front
        self.assertEqual(seen[-1], (len(res), len(res)))
        done = [d for d, _ in seen]
        self.assertEqual(done, sorted(done))      # never counts backwards

    def test_progress_total_respects_max_tracks(self):
        seen = []
        random.seed(0)
        build_warmup_playlist(_pool(), max_tracks=30,
                              progress_cb=lambda d, t: seen.append((d, t)))
        self.assertEqual(seen[0], (0, 30))

    def test_progress_total_ignores_unused_social_pools(self):
        """Mode pools stay in `pools` when Modetänze are off — they must not
        inflate the denominator."""
        seen = []
        random.seed(0)
        build_warmup_playlist(_pool(n=10, social=5), include_modetaenze=False,
                              progress_cb=lambda d, t: seen.append((d, t)))
        self.assertEqual(seen[0], (0, 100))       # not 100 + 30 social


if __name__ == "__main__":
    unittest.main()
