#!/usr/bin/env python3
"""Once every Paso Doble has played, the next ones go round again.

Run:  py -m unittest tests.planner.test_pd_variety -v

L15: Paso Doble is the one dance allowed to repeat, and the soft no-repeat set
kept it varied only until each in-tempo title had been used once. After that
the whole pool was open again and the score decided: the most-played Paso Doble
won nearly every heat (every heat under 'proven'), often twice in a row. The
repeats now cycle through the least-used titles, never the previous heat's.
"""

import unittest
from collections import Counter
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary, PlaylistSuggester
from planner.models import RoundConfig


def _paso(name: str, pop: int) -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\PD\{name} (PD 60).mp3"),
        title=name, dance="PD", bpm=None, popularity=pop)


class PasoVarietyTest(unittest.TestCase):

    def _round(self, pasos, heats=7, strategy="proven", seed=0, pd_used=None):
        lib = MusicLibrary()
        lib.entries.extend(pasos)
        sugg = PlaylistSuggester(lib, seed=seed)
        rc = RoundConfig(name="Vorrunde", heats=heats, tier="early", strategy=strategy)
        if pd_used is not None:
            heats = sugg.regenerate_round(rc, ["PD"], "S", set(), pd_used,
                                          use_timbre=False, style="Latin")
        else:
            heats = sugg.suggest("S", [rc], ["PD"], use_timbre=False,
                                 style="Latin")["Vorrunde"]
        return [h[0].title for h in heats]

    def _three(self):
        return [_paso("Espana Cani", 9), _paso("El Gato Montes", 3),
                _paso("Amparito Roca", 1)]

    def test_the_repeats_cycle_through_every_paso(self):
        for strategy in ("proven", "mixed", "all"):
            for seed in range(20):
                names = self._round(self._three(), heats=6, strategy=strategy, seed=seed)
                self.assertEqual(set(Counter(names).values()), {2},
                                 (strategy, seed, names))

    def test_no_paso_plays_twice_in_a_row(self):
        for strategy in ("proven", "mixed", "all"):
            for seed in range(20):
                names = self._round(self._three(), strategy=strategy, seed=seed)
                for a, b in zip(names, names[1:], strict=False):
                    self.assertNotEqual(a, b, (strategy, seed, names))

    def test_a_re_rolled_round_cycles_too(self):
        pasos = self._three()
        others = {str(pasos[0].path)}        # another round already has it
        for seed in range(20):
            names = self._round(pasos, heats=5, seed=seed, pd_used=set(others))
            self.assertEqual(names[:2].count("Espana Cani"), 0, names)
            for a, b in zip(names, names[1:], strict=False):
                self.assertNotEqual(a, b, (seed, names))

    def test_out_of_tempo_pasos_still_fill_the_heats(self):
        pasos = self._three()
        for e in pasos:
            e.bpm = 10
        self.assertEqual(len(self._round(pasos, heats=5)), 5)

    def test_a_round_without_an_in_tempo_paso_repeats_one_already_played(self):
        # Marcel: "no, use a one we already played" - a round whose own history
        # has only out-of-tempo Pasos replays an in-tempo one from earlier on.
        good, slow = _paso("Espana Cani", 9), _paso("Slow Paso", 9)
        slow.bpm = 10
        lib = MusicLibrary()
        lib.entries.extend([good, slow])
        rounds = [RoundConfig(name="Vorrunde", heats=1, tier="early", strategy="mixed"),
                  RoundConfig(name="Finale", heats=2, tier="final", strategy="mixed")]
        for seed in range(10):
            pl = PlaylistSuggester(lib, seed=seed).suggest(
                "S", rounds, ["PD"], use_timbre=False, style="Latin",
                round_pools=[[good], [slow]])
            self.assertEqual([h[0].title for h in pl["Finale"]],
                             ["Espana Cani"] * 2, seed)

    def test_a_re_rolled_round_without_an_in_tempo_paso_repeats_a_played_one(self):
        good, slow = _paso("Espana Cani", 9), _paso("Slow Paso", 9)
        slow.bpm = 10
        lib = MusicLibrary()
        lib.entries.extend([good, slow])
        rc = RoundConfig(name="Finale", heats=2, tier="final", strategy="mixed")
        heats = PlaylistSuggester(lib, seed=0).regenerate_round(
            rc, ["PD"], "S", set(), {str(good.path)}, use_timbre=False,
            style="Latin", candidates=[slow])
        self.assertEqual([h[0].title for h in heats], ["Espana Cani"] * 2)

    def test_a_single_paso_still_fills_every_heat(self):
        names = self._round([_paso("Espana Cani", 9)], heats=4)
        self.assertEqual(names, ["Espana Cani"] * 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
