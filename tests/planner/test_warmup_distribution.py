#!/usr/bin/env python3
"""How often each dance actually turns up in a generated 🤸 Eintanzen / party list.

Run:  py -m unittest tests.planner.test_warmup_distribution -v

`_ETDS_PROB` states an intended appearance weight per dance, each section
summing to 1. The list is not built by sampling those weights directly, though:
a round takes THREE DISTINCT dances out of five, overdue core dances are pulled
in before the weighted fill, and Wiener Walzer / Paso Doble sit behind a
late-gate. Every one of those rules bends the resulting distribution.

So this module measures the real thing — many builds over a pool deep enough
that nothing runs dry — and pins what the weights do and do not survive:

* what holds — nobody starves, a heavier weight beats a clearly lighter one,
  the mid-field lands near its nominal share, and the lead dance of a section
  (LW / RB) never sits out two rounds running;
* what does not — 3-distinct-of-5 holds any dance to about a third, so LW and
  RB can never reach their stated 0.40, and the rarest dance of a section is
  lifted to several times its weight by being the last one left to draw from.

The two "does not" tests are measurements of a known gap, not an endorsement of
it: change the coverage rule or the weights and they are meant to be re-read.
"""

import random
import unittest
from collections import Counter
from pathlib import Path

from planner import warmup as w
from planner.models import MusicEntry

_BAL = w._WARMUP_BALLROOM
_LAT = w._WARMUP_LATIN

# 20 lists of 240 out of 300-per-dance pools: enough samples that the shares are
# stable to ~0.01 across seeds, and still well under a second.
_RUNS = 20
_LEN = 240
_POOL = 300


def _pool():
    return [MusicEntry(path=Path(f"C:/lib/{d}/{d}_{i}.mp3"), title=f"{d} {i}",
                       dance=d, bpm=30)
            for d in _BAL + _LAT for i in range(_POOL)]


class DistributionTest(unittest.TestCase):
    """Shares measured once for the whole class — the builds are the slow part."""

    @classmethod
    def setUpClass(cls):
        # Shares alone hide what an operator actually sees — a round at a time —
        # so record the rounds as the builder plans them. Slicing the finished
        # list in threes used to stand in for that, and cannot any more: a round
        # can come out SHORT when every dance left is ruled out, so the slices
        # drift out of step with the real rounds after the first short one.
        # One entry per build, because each build starts its own history: the
        # last round of one list and the first of the next are not neighbours.
        cls.rounds = {_BAL: [], _LAT: []}
        real_round = w._warmup_section_round
        current: dict = {}

        def spy(result, pools, section, **kw):
            took = real_round(result, pools, section, **kw)
            if took:
                current[section].append(tuple(kw["rounds"][-1]))
            return took

        random.seed(20260823)
        counts = Counter()
        cls.lists = []
        w._warmup_section_round = spy
        try:
            for _ in range(_RUNS):
                current.clear()
                current.update({_BAL: [], _LAT: []})
                got = w.build_warmup_playlist(_pool(), max_tracks=_LEN)
                cls.lists.append([w.warmup_code(e) for e in got])
                counts.update(cls.lists[-1])
                for section in (_BAL, _LAT):
                    cls.rounds[section].append(list(current[section]))
        finally:
            w._warmup_section_round = real_round
        cls.counts = counts
        cls.share = {}
        for section in (_BAL, _LAT):
            total = sum(counts[d] for d in section)
            for d in section:
                cls.share[d] = counts[d] / total

    def _ratio(self, dance):
        """Measured share ÷ the share `_ETDS_PROB` asks for."""
        return self.share[dance] / w._ETDS_PROB[dance]

    def _all_rounds(self, section):
        """Every round of the section, the build boundaries forgotten."""
        return [rnd for build in self.rounds[section] for rnd in build]

    def test_each_section_of_the_weight_table_sums_to_one(self):
        for section in (_BAL, _LAT, w._WARMUP_MODE):
            self.assertAlmostEqual(sum(w._ETDS_PROB[d] for d in section), 1.0,
                                   places=3)

    def test_no_dance_starves(self):
        # 0.015, not the Paso's own measured share: PD sits at 0.0209 +- 0.001
        # (60 builds x 15 master seeds), so a 0.02 bound is ON the value rather
        # than under it and passed only on this class's one pinned seed - it
        # read 0.0192 on most others, before and after the LW/WW round fix
        # alike. A dance that actually starves reads near zero, which 0.015
        # still catches.
        for d in _BAL + _LAT:
            self.assertGreater(self.share[d], 0.015, f"{d} barely appears")

    def test_the_heavier_weight_wins(self):
        """Pairs whose intended weights are far enough apart to be decidable —
        CC vs JI (0.2375 vs 0.2125) is inside the noise and is left out."""
        for hi, lo in (("RB", "CC"), ("RB", "JI"), ("CC", "SA"), ("JI", "SA"),
                       ("SA", "PD"),
                       ("LW", "TG"), ("LW", "QS"), ("LW", "SF"),
                       ("TG", "WW"), ("QS", "WW"), ("SF", "WW")):
            self.assertGreater(self.share[hi], self.share[lo],
                               f"{hi} ({w._ETDS_PROB[hi]}) should outplay "
                               f"{lo} ({w._ETDS_PROB[lo]})")

    def test_the_mid_field_lands_near_its_weight(self):
        """Every dance the structural rules do not distort: within 40 % of the
        share `_ETDS_PROB` asks for. Slow Foxtrot rides highest of them (~1.36):
        it is in the coverage set while the Wiener Walzer, its only rival for
        the fourth Standard slot, is held back by "late WW" — and it is the
        likeliest dance to be drawn into the slot a deferred waltz frees (see
        the LW/WW rule in `_warmup_section_round`), which took it from ~1.29 to
        ~1.36 across three master seeds at 60 builds each. delta was 0.35 and
        had no room left for that."""
        for d in ("SA", "CC", "JI", "TG", "QS", "SF"):
            self.assertAlmostEqual(self._ratio(d), 1.0, delta=0.40,
                                   msg=f"{d}: {self.share[d]:.3f} measured vs "
                                       f"{w._ETDS_PROB[d]:.3f} intended")

    # ── the two measured gaps ────────────────────────────────────────────────

    def test_a_lead_dances_stated_weight_stays_out_of_reach(self):
        """A round plays three DIFFERENT dances, so a dance is held to roughly a
        third of its section however the weights are tuned — and LW and RB are
        asked for 0.40. They are in 95 % of their rounds and still deliver ~0.32,
        four fifths of what the table wants. A third is not quite a hard ceiling
        any more: a round that comes out short because every remaining dance was
        ruled out gives whoever is in it more than a third."""
        for d in _BAL + _LAT:
            self.assertLess(self.share[d], 0.36)
        for d in ("LW", "RB"):
            self.assertGreater(w._ETDS_PROB[d], 1 / 3)      # asked for
            self.assertLess(self._ratio(d), 0.90)           # delivered

    def test_the_rarest_dance_of_a_section_outruns_its_weight_in_the_fill(self):
        """A round is filled from what is LEFT, and `_warmup_pick` renormalises
        the weights over it: once the lead and the overdue dances are in and the
        no-rut rule has taken out whoever played the last two rounds, the rarest
        dance is often the only one still eligible, so its 0.05 weight is drawn
        against a two-dance field. The Wiener Walzer comes out at ~1.5× what the
        table asks — measured, not endorsed. (It read ~1.48 while the Wiener was
        simply dropped from any round it shared with a Langsamer Walzer, and
        ~1.60 while the two were separated inside the round. Under the deferral
        that replaced both it is 1.45-1.54 across three master seeds at 60
        builds each: the Wiener is no longer lost to the collision, but the
        round it is handed to may have no slot for it either.)

        The Paso escapes that because it is out of the fill altogether —
        whichever way its switch is set — and placed on its own percentage
        instead (see `_PD_ROUND_RATE`), which the renormalised draw never could.
        It lands just UNDER its weight: the 40-track gate forfeits the Latin
        rounds at the start of the evening, exactly as the switch asks."""
        self.assertGreater(self._ratio("WW"), 1.2)
        # delta 0.3, measured: the PD ratio runs 0.77-0.96 across 15 master
        # seeds at 60 builds each (mean 0.836). The LW/WW rule is a Standard-
        # section rule and leaves it alone — 0.83-0.85 under the deferral.
        # delta=0.2 fitted the pinned seed, not the spread.
        self.assertAlmostEqual(self._ratio("PD"), 1.0, delta=0.3)

    # ── the rules the weights are bent by ────────────────────────────────────

    def test_the_late_gates_hold(self):
        """No Paso Doble in the first 40 tracks, no Wiener Walzer in the first 12."""
        for codes in self.lists:
            self.assertNotIn("PD", codes[:40])
            self.assertNotIn("WW", codes[:12])

    def test_the_lead_dance_never_sits_out_two_rounds_running(self):
        """LW and RB are weighted 0.40, above the 1/3 a three-dance round can
        give them, so one round without is the most the draw may take. The pool
        here is deep enough that they never simply run out."""
        for section in (_BAL, _LAT):
            lead = w._section_lead(section)
            self.assertIn(lead, ("LW", "RB"))
            for rounds in self.rounds[section]:
                for i in range(len(rounds) - 1):
                    self.assertTrue(lead in rounds[i] or lead in rounds[i + 1],
                                    f"{lead} missing from {rounds[i]} and "
                                    f"{rounds[i + 1]}")

    def test_the_lead_dance_leads_its_section(self):
        for section in (_BAL, _LAT):
            lead = w._section_lead(section)
            rounds = self._all_rounds(section)
            share = [sum(lead in r for r in rounds) / len(rounds)]
            self.assertGreater(share[0], 0.80)
            for d in section:
                if d != lead:
                    self.assertGreater(self.share[lead], self.share[d])

    def test_only_a_weight_a_round_cannot_deliver_makes_a_lead(self):
        """The rule keys off `_ETDS_PROB`, not off two hardcoded codes: retune
        the table below 1/3 and the guarantee retires by itself."""
        self.assertEqual(w._section_lead(_BAL), "LW")
        self.assertEqual(w._section_lead(_LAT), "RB")
        # A section whose heaviest dance fits inside a round needs no guarantee.
        self.assertIsNone(w._section_lead(("TG", "SF", "QS")))

    def test_samba_is_never_played_two_rounds_running(self):
        """Absolutely never, not "rarely". The round would rather hand another
        dance a third round running — the one rule that does yield — than put
        the Samba back on the floor a round early."""
        for rounds in self.rounds[_LAT]:
            for i in range(len(rounds) - 1):
                self.assertFalse("SA" in rounds[i] and "SA" in rounds[i + 1],
                                 f"Samba twice running: {rounds[i]} then "
                                 f"{rounds[i + 1]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
