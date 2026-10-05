#!/usr/bin/env python3
"""The ↺ re-roll of a Paso Doble slot picks a Paso Doble the list doesn't have.

Run:  py -m unittest tests.planner.test_pd_regenerate -v

The GUI hands `regenerate` every path already planned, the slot's own song
included. The Paso Doble pool only looked at the soft set a whole-playlist
generation fills, so for a re-roll it saw nothing excluded: the ↺ could hand
back the very song it was asked to replace, or one already in another round.
Paso Doble may still repeat when the library has no other: that is the one
dance allowed to, and the day planner relies on it (tests.planner.test_day_plan).
"""

import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary, PlaylistSuggester


def _entry(name: str, dance: str = "PD") -> MusicEntry:
    return MusicEntry(
        path=Path(rf"C:\music\tanzcds\lateincd\{dance}\{name}.mp3"),
        title=name, dance=dance, bpm=None, popularity=3)


class PasoRegenerateTest(unittest.TestCase):

    def setUp(self):
        self.pasos = [_entry(f"Paso {i} (PD 60)") for i in range(8)]
        lib = MusicLibrary()
        lib.entries.extend(self.pasos)
        self.sugg = PlaylistSuggester(lib)

    def _regen(self, exclude):
        return self.sugg.regenerate("PD", "S", "early", exclude,
                                    use_timbre=False, style="Latin")

    def test_a_re_roll_never_returns_a_paso_already_planned(self):
        free = self.pasos[-1]
        exclude = {str(e.path) for e in self.pasos if e is not free}
        for _ in range(40):
            self.assertEqual(self._regen(exclude).path, free.path)

    def test_a_paso_repeats_when_the_library_has_no_other(self):
        exclude = {str(e.path) for e in self.pasos}
        self.assertIsNotNone(self._regen(exclude))


if __name__ == "__main__":
    unittest.main(verbosity=2)
