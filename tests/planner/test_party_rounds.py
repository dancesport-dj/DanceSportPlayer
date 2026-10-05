#!/usr/bin/env python3
"""Tests for the shape of an ETDS party round.

Run:  py -m unittest tests.planner.test_party_rounds -v

test_warmup.py checks that the builder produces a list at all and that the
options do what they say. This file checks the RHYTHM of the evening — how
often a social round is a double, what opens it — because that is what the
floor notices and none of it can be read off a single seeded list.

The round builders are called directly rather than through
`build_warmup_playlist`: reconstructing rounds from the flat list means
guessing where one ended, and with a finite pool the tail of a long list is all
misses anyway.
"""

import random
import unittest
from pathlib import Path

from planner.models import MusicEntry
from planner.warmup import (
    _WARMUP_BALLROOM,
    _WARMUP_LATIN,
    _WARMUP_MODE,
    _warmup_mode_round,
    _warmup_section_round,
    warmup_code,
)

_LABEL = {"DISCOFOX": "Discofox", "SALSA": "Salsa", "BACHATA": "Bachata",
          "WCS": "West Coast Swing", "KIZOMBA": "Kizomba", "FORRO": "Forró"}

_STYLE_DIR = {d: ("lateincd" if d in _WARMUP_LATIN else "standardcd")
              for d in _WARMUP_BALLROOM + _WARMUP_LATIN}


def _entry(dance: str, i: int) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\{_STYLE_DIR[dance]}\{dance}\{dance}{i}.mp3"),
        title=f"{dance} {i}", dance=dance, duration=180)


def _social(code: str, i: int) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\others\{code}\{code}{i}.mp3"),
        title=f"{_LABEL[code]} {i}", dance=None, other_genre=_LABEL[code],
        duration=180)


def _section_rounds(n: int, section, *, late_ww=True, late_pd=True,
                    seed: int = 0, per: int = 400) -> list[list[str]]:
    """`n` rounds of one section, each as the dance codes it planned.

    Deep pools on purpose: with 40 tracks a dance the pools run dry inside a
    long evening and the tail of the list is all misses, which reads as a
    coverage hole that the rules never caused."""
    random.seed(seed)
    pools = {d: [_entry(d, i) for i in range(per)] for d in section}
    result: list = []
    rounds: list[list[str]] = []
    deferred: list[str] = []
    for _ in range(n):
        if not _warmup_section_round(result, pools, section, late_ww=late_ww,
                                     late_pd=late_pd, rounds=rounds,
                                     deferred=deferred):
            break
    return rounds


def _windows(rounds, size=3):
    for i in range(len(rounds) - size + 1):
        yield rounds[i:i + size]


def _mode_rounds(n: int, dances=None, seed: int = 7,
                 first: bool = False) -> list[list[str]]:
    """`n` social rounds, each as the list of dance codes it planned. Every round
    gets a full pool, so nothing here is an artefact of a pool running dry.

    `first` asks for `n` rounds that are each the evening's FIRST social round,
    not one evening's first round followed by `n-1` later ones."""
    random.seed(seed)
    dances = list(dances or _WARMUP_MODE)
    out = []
    for _ in range(n):
        pools = {d: [_social(d, i) for i in range(4)] for d in dances}
        result: list = []
        _warmup_mode_round(result, pools, dances, first=first)
        out.append([warmup_code(e) for e in result])
    return out


class SocialRoundSizeTest(unittest.TestCase):
    """"1:2": one double social round for every two singles."""

    def test_a_third_of_the_social_rounds_hold_two_titles(self):
        sizes = [len(r) for r in _mode_rounds(3000)]
        self.assertEqual(set(sizes), {1, 2})
        share = sizes.count(2) / len(sizes)
        self.assertAlmostEqual(share, 1 / 3, delta=0.04,
                               msg=f"{share:.0%} of the social rounds are doubles")

    def test_the_ratio_holds_whichever_seed_the_evening_starts_on(self):
        for seed in range(5):
            with self.subTest(seed=seed):
                sizes = [len(r) for r in _mode_rounds(1500, seed=seed)]
                self.assertAlmostEqual(sizes.count(2) / len(sizes), 1 / 3,
                                       delta=0.05)


class SocialRoundOpenerTest(unittest.TestCase):
    """Discofox leads a double — it is what the floor fills up to."""

    def test_every_two_title_round_opens_with_discofox(self):
        doubles = [r for r in _mode_rounds(2000) if len(r) == 2]
        self.assertTrue(doubles)
        self.assertEqual({r[0] for r in doubles}, {"DISCOFOX"})

    def test_the_second_title_is_some_other_social_dance(self):
        doubles = [r for r in _mode_rounds(2000) if len(r) == 2]
        seconds = {r[1] for r in doubles}
        self.assertNotIn("DISCOFOX", seconds)
        self.assertGreater(len(seconds), 1)

    def test_a_single_title_round_is_not_forced_to_discofox(self):
        singles = [r[0] for r in _mode_rounds(2000) if len(r) == 1]
        self.assertTrue(singles)
        self.assertIn("DISCOFOX", singles)          # allowed
        self.assertTrue(set(singles) - {"DISCOFOX"})  # but not the only one

    def test_the_evenings_first_social_title_is_always_a_discofox(self):
        """The floor has to be opened, and Discofox is what opens it — so the
        first social round leads with it whether it is a single or a double."""
        rounds = _mode_rounds(2000, first=True)
        self.assertEqual({r[0] for r in rounds}, {"DISCOFOX"})

    def test_the_first_round_is_no_longer_or_shorter_for_it(self):
        """Only WHICH dance opens changes, not the 1:2 double-to-single ratio."""
        sizes = [len(r) for r in _mode_rounds(3000, first=True)]
        self.assertEqual(set(sizes), {1, 2})
        self.assertAlmostEqual(sizes.count(2) / len(sizes), 1 / 3, delta=0.04)

    def test_an_unticked_discofox_leaves_the_first_round_a_weighted_pick(self):
        rounds = _mode_rounds(1500, dances=["SALSA", "BACHATA", "WCS"],
                              first=True)
        self.assertNotIn("DISCOFOX", {c for r in rounds for c in r})
        self.assertGreater(len({r[0] for r in rounds}), 1)

    def test_without_discofox_a_double_is_two_weighted_picks(self):
        """Unticked Discofox must not leave the doubles one title short."""
        rounds = _mode_rounds(1500, dances=["SALSA", "BACHATA", "WCS"])
        self.assertNotIn("DISCOFOX", {c for r in rounds for c in r})
        doubles = [r for r in rounds if len(r) == 2]
        self.assertAlmostEqual(len(doubles) / len(rounds), 1 / 3, delta=0.05)
        self.assertGreater(len({r[0] for r in doubles}), 1)


class ThreeRoundCoverageTest(unittest.TestCase):
    """Every dance of a section inside any three rounds it is part of.

    The old rule looked back over "the last six tracks of this section", which
    is two rounds only while every round is three tracks long — and a Standard
    round is not always three. Rounds are now counted as rounds."""

    def _assert_covered(self, rounds, want, label):
        for i, win in enumerate(_windows(rounds)):
            played = {d for rnd in win for d in rnd}
            missing = sorted(set(want) - played)
            self.assertFalse(missing, f"{label}: rounds {i}-{i + 2} never "
                                      f"played {missing} — {win}")

    def test_the_standard_rounds_cover_lw_tg_sf_qs(self):
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(40, _WARMUP_BALLROOM, seed=seed)
                self._assert_covered(rounds, ("LW", "TG", "SF", "QS"),
                                     f"seed {seed}")

    def test_the_latin_rounds_cover_sa_cc_rb_ji(self):
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(40, _WARMUP_LATIN, seed=seed)
                self._assert_covered(rounds, ("SA", "CC", "RB", "JI"),
                                     f"seed {seed}")

    def test_an_unticked_late_ww_puts_the_wiener_in_the_guarantee(self):
        """"All five dances" is all five — the Wiener Walzer only sits outside
        the guarantee while the operator has asked for it late."""
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(40, _WARMUP_BALLROOM, late_ww=False,
                                         seed=seed)
                self._assert_covered(rounds, _WARMUP_BALLROOM, f"seed {seed}")

    def test_the_paso_stays_out_of_the_guarantee_either_way(self):
        """The Wiener Walzer joins the guarantee when its switch comes off; the
        Paso never does. "It not makes sense to enforce PD in 3 rounds" — at a
        weight of 0.025 a guaranteed Paso every third round is 13 times what
        the table asks, so the switch only decides how early it may start."""
        for late_pd in (True, False):
            for seed in range(6):
                with self.subTest(late_pd=late_pd, seed=seed):
                    rounds = _section_rounds(40, _WARMUP_LATIN,
                                             late_pd=late_pd, seed=seed)
                    self._assert_covered(rounds, ("SA", "CC", "RB", "JI"),
                                         f"seed {seed}")
                    windows = [rounds[i:i + 3] for i in range(len(rounds) - 2)]
                    self.assertTrue(
                        any("PD" not in {d for r in win for d in r}
                            for win in windows),
                        f"seed {seed}: a Paso in every three-round window")

    def test_the_first_three_rounds_are_the_base_then_the_other_two(self):
        """LW TG QS opens; the two that were not in it come in next."""
        rounds = _section_rounds(3, _WARMUP_BALLROOM, late_ww=False, seed=0)
        self.assertEqual(rounds[0], ["LW", "TG", "QS"])
        self.assertTrue({"SF", "WW"} <= {d for rnd in rounds[1:] for d in rnd},
                        f"SF / WW did not follow the base round: {rounds}")


class NoRutTest(unittest.TestCase):
    """"SF 3 rounds after each other — that seems odd."" It is: a dance that
    played in both of the last two rounds sits this one out. Only the lead
    dance (LW / RB) is asked for often enough to earn a third round running.

    It is the one rule that yields, though, and only to keep a round at three
    dances — the Latin section has four dances to fill three slots and simply
    runs out of legal ones. See `test_a_full_round_outranks_the_rut_rule`."""

    def _runs(self, rounds, dance) -> int:
        """Longest run of consecutive rounds holding `dance`."""
        best = run = 0
        for rnd in rounds:
            run = run + 1 if dance in rnd else 0
            best = max(best, run)
        return best

    def test_a_full_round_outranks_the_rut_rule(self):
        """"We must have in each round 3 dances."

        The Latin section cannot have both. Its fill is SA/CC/RB/JI — the Paso
        is placed on its own percentage, not drawn — and the Samba may not play
        two rounds running, so every other round has exactly CC, RB and JI to
        offer. Two of those in a row and all three are in their third round.
        Four dances into three slots leaves one out per round, so over any
        three rounds at least one dance played all three; there is no ordering
        that avoids it.

        So the rut rule yields first and the round stays full. What does NOT
        yield is the Samba spacing and the Paso's — those the operator asked
        for by name, and they hold below."""
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(60, _WARMUP_LATIN, seed=seed)
                self.assertEqual({len(r) for r in rounds}, {3},
                                 f"seed {seed}: a short round in {rounds}")
                for d in ("SA", "PD"):
                    self.assertLessEqual(self._runs(rounds, d), 1,
                                         f"{d} ran {self._runs(rounds, d)} "
                                         f"rounds in a row (seed {seed})")

    def test_the_standard_rounds_keep_the_rut_rule(self):
        """Five dances for three slots leaves the room the Latin four do not:
        with "late WW" off nothing but the lead sees a third round running."""
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(60, _WARMUP_BALLROOM, late_ww=False,
                                         seed=seed)
                self.assertEqual({len(r) for r in rounds}, {3})
                for d in ("TG", "WW", "SF", "QS"):
                    self.assertLessEqual(self._runs(rounds, d), 2,
                                         f"{d} ran {self._runs(rounds, d)} "
                                         f"rounds in a row (seed {seed})")

    def test_the_lead_dance_may_run_on(self):
        """LW is weighted at 0.40, which a third of a round cannot deliver —
        holding it to two rounds running would starve it."""
        rounds = _section_rounds(60, _WARMUP_BALLROOM, seed=0)
        self.assertGreater(self._runs(rounds, "LW"), 2)


class LatePasoSpacingTest(unittest.TestCase):
    """"Late PD" asks for a rare Paso, not just a late one.

    The track gate only held it back until the list was 40 long; after that the
    Paso turned up in a third of all Latin rounds, because once the lead and the
    overdue dances are placed and the no-rut rule has taken out whoever played
    the last two rounds, it is often the only dance left to draw from. Three
    complete Latin rounds now have to pass between two Pasos."""

    def _gaps(self, rounds) -> list[int]:
        at = [i for i, rnd in enumerate(rounds) if "PD" in rnd]
        return [b - a - 1 for a, b in zip(at, at[1:])]

    def test_three_latin_rounds_lie_between_two_pasos(self):
        # A long evening on purpose: past the 40-track gate and its own weight
        # a short one can hold a single Paso, which says nothing about spacing.
        for seed in range(6):
            with self.subTest(seed=seed):
                rounds = _section_rounds(400, _WARMUP_LATIN, seed=seed)
                gaps = self._gaps(rounds)
                self.assertTrue(gaps, f"seed {seed}: fewer than two Pasos")
                self.assertGreaterEqual(min(gaps), 3,
                                        f"seed {seed}: Latin rounds between two "
                                        f"Pasos {gaps} — {rounds}")

    def test_the_paso_lands_on_its_own_percentage_not_on_what_is_left(self):
        """"It should be placed based on his percentage … so we only get spare
        PD in the evening, f.e. 3 titles played."

        The spacing alone does not deliver that. `_warmup_pick` renormalises the
        weights over whoever is still eligible, and with five dances filling
        three slots the Paso is regularly the only one left — which turned its
        0.025 into a sixth of all Latin rounds. Offered at its own weight it
        lands where the table asks: 0.025 of three slots is one round in
        thirteen."""
        rounds = _section_rounds(400, _WARMUP_LATIN, seed=0)
        share = sum("PD" in rnd for rnd in rounds) / len(rounds)
        self.assertGreater(share, 0.01, "the Paso never played at all")
        self.assertLess(share, 0.12, f"a Paso in {share:.0%} of the Latin rounds")

    def test_an_evening_holds_a_handful_of_pasos(self):
        """The number the operator actually reads off the finished list."""
        counts = []
        for seed in range(8):
            rounds = _section_rounds(40, _WARMUP_LATIN, seed=seed)
            counts.append(sum("PD" in rnd for rnd in rounds))
        mean = sum(counts) / len(counts)
        self.assertAlmostEqual(mean, 3, delta=2,
                               msg=f"Pasos per 40 Latin rounds: {counts}")

    def test_an_unticked_late_pd_drops_the_track_gate_and_nothing_else(self):
        """"If I untick late PD it should still use percentage, it not makes
        sense to enforce PD in 3 rounds."

        The switch says WHEN the Paso may first turn up, not how often. Untick
        it and the Paso is free from the first round on — but it is still drawn
        on its own percentage, still three rounds apart, and still never forced
        in by the coverage rule, because a dance weighted 0.025 has no business
        in every third round either way."""
        rounds = _section_rounds(400, _WARMUP_LATIN, late_pd=False, seed=0)
        gaps = self._gaps(rounds)
        self.assertGreaterEqual(min(gaps), 3,
                                f"Latin rounds between two Pasos {gaps}")
        share = sum("PD" in rnd for rnd in rounds) / len(rounds)
        self.assertLess(share, 0.15, f"a Paso in {share:.0%} of the Latin rounds")

    def test_only_the_track_gate_tells_the_two_switch_settings_apart(self):
        """Ticked, the Paso waits for a list 40 tracks long; unticked it can
        open the evening. Over the same seeds that is the whole difference."""
        early = [_section_rounds(14, _WARMUP_LATIN, late_pd=False, seed=s)
                 for s in range(12)]
        late = [_section_rounds(14, _WARMUP_LATIN, late_pd=True, seed=s)
                for s in range(12)]
        self.assertGreater(sum(any("PD" in r for r in rs) for rs in early), 0,
                           "unticked, the Paso still never came early")
        self.assertEqual(sum(any("PD" in r for r in rs) for rs in late), 0,
                         "ticked, a Paso slipped in under the 40-track gate")


if __name__ == "__main__":
    unittest.main(verbosity=2)
