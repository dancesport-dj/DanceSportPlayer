#!/usr/bin/env python3
"""The old / rest / all-songs markers are words, not letters inside a name.

Run:  py -m unittest tests.planner.test_superseded_words -v

`_is_superseded_playlist` looked for "alt(e)", "rest" and "alle" anywhere in a
folder or file name, so a tournament in Altenkirchen, a list from Bukarest, a
"Walter-Kolb-Cup" folder or a Ballett set was taken for an old version, a
left-over list or an all-songs dump — and never counted for popularity. A
marker now has to stand on its own: at the start, after a separator or a digit,
as a camelCase hump (neuAlleLAT, latRest) or glued to an acronym (STDalt).

The "kept out" names below are the real ones from the tournament folder; every
one of them was excluded before and has to stay excluded.
"""

import unittest

from planner import competition
from planner.competition import _is_superseded_playlist


def _excluded(rel: str) -> bool:
    return _is_superseded_playlist(competition.PLAYLIST_DIR / rel)


class SupersededWordsTest(unittest.TestCase):

    def test_real_event_names_are_learned_from(self):
        for rel in ("Altenkirchen 2024/HGR B STD.m3u",
                    "ALTENKIRCHEN/HGR B STD.m3u",
                    "Kaltenkirchen Pokal/HGR D LAT.m3u",
                    "Walter-Kolb-Cup/HGR S STD.m3u",
                    "Turniere 2023/Walter Cup HGR A LAT.m3u",
                    "WDSF Open Bukarest/HGR S STD.m3u",
                    "Bukarest HGR S LAT.m3u",
                    "Ballett Gala/HGR C STD.m3u",
                    "Ballett Gala HGR C STD.m3u",
                    "Halle 2019/HGR C STD.m3u",
                    "Turnier Halle 2019.m3u",
                    "HGR A LAT Walter Cup.m3u",
                    "Abschlussveranstaltung/HGR D STD.m3u"):
            with self.subTest(rel=rel):
                self.assertFalse(_excluded(rel))

    def test_the_markers_still_keep_old_rest_and_all_lists_out(self):
        for rel in ("alt/HGR B STD.m3u",
                    "alte/HGR B STD.m3u",
                    "alter stand senii2/HGR B STD.m3u",
                    "07.8.2011alt/HGR B STD.m3u",
                    "DP HGR 2 S LAT_alt.m3u",
                    "SEN I S STDalt.m3u",
                    "HGR B LAT_alteListeNotfall.m3u",
                    "modetaenze_alt.m3u",
                    "rest.m3u", "reste.m3u", "restgut.m3u", "restz.m3u",
                    "latRest.m3u", "eintanzenRest.m3u", "eintanzenDCReste.m3u",
                    "qresteauswahl.m3u", "hgr_rangliste_rest.m3u",
                    "OPEN_CLOSED_STD_REST.m3u", "BREITENSPORT_LAT_REST_.m3u",
                    "alle.m3u", "ALLE_LAT.m3u", "alleSTD.m3u", "allestd.m3u",
                    "allle.m3u", "allerest.m3u", "neuAlleLAT.m3u", "resteAlle.m3u",
                    "alleNeu2016.m3u", "LATKOMPLETT.m3u", "latkomplett.m3u"):
            with self.subTest(rel=rel):
                self.assertTrue(_excluded(rel))


if __name__ == "__main__":
    unittest.main(verbosity=2)
