#!/usr/bin/env python3
"""The lists an event danced in earlier years, round by round and dance by dance.

Run:  py -m unittest tests.planner.test_event_history -v

Planning the DanceConvention 2026 starts from what the DanceConvention 2025
(and 2024, …) played for the same competition. Those lists sit in one folder
per edition — 'DanceConvention 2025/HGR_S_STD.m3u' — and carry no round
marker: the preliminary heats come first, the final last. Which title was the
final's Slow Waltz is read per dance from the back, so a spare title at the
end of the list (2025's HGR S list holds 16 titles for 15 slots) only moves
its own dance.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from dancesport_planner import MusicEntry, MusicLibrary
from planner import event_plan
from planner.competition import (competition_matches_file,
                                 parse_competition_schedule)

_STD = ("LW", "TG", "WW", "SF", "QS")
_BPM = {"LW": 29, "TG": 32, "WW": 59, "SF": 29, "QS": 50,
        "CC": 31, "RB": 25}


def _path(title: str, dance: str) -> str:
    return rf"C:\music\standardcd\{title} ({dance} {_BPM[dance]}).mp3"


class EventSeriesTest(unittest.TestCase):

    def test_the_year_is_not_part_of_the_series(self):
        self.assertEqual(event_plan.event_series("DanceConvention 2025"),
                         "danceconvention")
        self.assertEqual(event_plan.event_series("DanceConvention 2024"),
                         event_plan.event_series("DanceConvention 2025"))

    def test_spelling_of_the_name_does_not_split_a_series(self):
        self.assertEqual(event_plan.event_series("WIDAFE 2017"),
                         event_plan.event_series("WiDaFe 2014"))

    def test_a_dated_folder_keeps_its_event_words(self):
        self.assertEqual(
            event_plan.event_series("07.12.2024 Weihnachtsparty Willich"),
            "weihnachtsparty willich")

    def same_series(self, *folders):
        series = {event_plan.event_series(f) for f in folders}
        self.assertEqual(len(series), 1, series)
        return series.pop()

    def test_dc_is_dancecomp(self):
        self.assertEqual(self.same_series("dC2013", "danceComp 2014", "DanceComp 2026"),
                         "dancecomp")

    def test_etds_wherever_it_is_held(self):
        self.same_series("ETDS Mohnheim 2025", "ETDS Seesen 2023")

    def test_every_ball_is_one_event(self):
        self.same_series("Ball 2024 BostonClub", "Ball Boston-Club 02.12.2023",
                         "Ball Recklinghausen 2025", "30.11.2013 Galaball")

    def test_every_ranking_tournament_is_one_event(self):
        self.same_series("09.10.2021 Ranglisten BC", "Rangliste BC 29.2.17",
                         "BC Rangliste 17.2.19",
                         "20.02.2016 (u. 21.) Ranglisten STD BostonClub",
                         "22.02.2015 Rangliste Sen1S STD")

    def test_other_dc_folders_stay_what_they_were(self):
        """'DC' is also the D-to-C class: only a folder named dC alone is DanceComp."""
        self.assertEqual(event_plan.event_series("11.06.2022 DC HGR A LAT"), "dc hgr a lat")
        self.assertEqual(event_plan.event_series("DanceConvention 2025"), "danceconvention")

    def test_a_merged_event_is_listed_once_by_its_own_name(self):
        root = Path(tempfile.mkdtemp(prefix="dp_series_"))
        self.addCleanup(shutil.rmtree, root, True)
        for name in ("Ball 2024 BostonClub", "Ball Recklinghausen 2025",
                     "ETDS Seesen 2023", "ETDS Mohnheim 2025", "dC2013", "DanceComp 2026"):
            (root / name).mkdir()
        self.assertEqual(event_plan.event_series_list(root),
                         [("ball", "Ball", 2), ("dancecomp", "DanceComp", 2),
                          ("etds", "ETDS", 2)])
        self.assertEqual([d.name for d in event_plan.past_editions("etds", root=root)],
                         ["ETDS Mohnheim 2025", "ETDS Seesen 2023"])
        self.assertEqual(event_plan.event_series("Ranglisten BC"),
                         event_plan.event_series("BC Rangliste 17.2.19"))


class EventHistoryTest(unittest.TestCase):

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="dp_event_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.lib = MusicLibrary()

    def entry(self, title, dance):
        e = MusicEntry(path=Path(_path(title, dance)), title=title,
                       dance=dance, bpm=_BPM[dance])
        self.lib.entries.append(e)
        return e

    def write(self, rel, entries):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#EXTM3U\n" + "\n".join(str(e.path) for e in entries)
                     + "\n", encoding="utf-8")
        return p

    def hgr_2025(self):
        """2-1 as the DJ played it: both preliminary heats of a dance back to
        back, then the final — and one spare Quickstep at the very end."""
        vr = [self.entry(f"VR{h} {d}", d) for d in _STD for h in (1, 2)]
        er = [self.entry(f"ER {d}", d) for d in _STD]
        spare = self.entry("Spare QS", "QS")
        self.write("DanceConvention 2025/HGR_S_STD.m3u", vr + er + [spare])
        return vr, er, spare

    # ── which folders are earlier editions ─────────────────────────────────

    def test_earlier_editions_newest_first(self):
        for name in ("DanceConvention 2024", "DanceConvention 2025",
                     "WiDaFe 2025", "12.03.2025 Krefeld"):
            (self.root / name).mkdir()
        found = event_plan.past_editions("danceconvention", root=self.root)
        self.assertEqual([p.name for p in found],
                         ["DanceConvention 2025", "DanceConvention 2024"])

    def test_the_edition_being_planned_is_not_its_own_history(self):
        for name in ("DanceConvention 2025", "DanceConvention 2026"):
            (self.root / name).mkdir()
        found = event_plan.past_editions("danceconvention", root=self.root,
                                         before_year=2026)
        self.assertEqual([p.name for p in found], ["DanceConvention 2025"])

    def test_the_series_to_choose_from(self):
        """The newest edition names the series; a folder without a year is
        no edition."""
        for name in ("DanceConvention 2024", "DanceConvention 2025",
                     "WiDaFe 2014", "WIDAFE 2017", "12.03.2025 Krefeld",
                     "Eintanzen"):
            (self.root / name).mkdir()
        (self.root / "loose.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        self.assertEqual(event_plan.event_series_list(root=self.root),
                         [("danceconvention", "DanceConvention", 2),
                          ("krefeld", "Krefeld", 1),
                          ("widafe", "WIDAFE", 2)])

    def test_no_playlist_folder_no_series(self):
        self.assertEqual(
            event_plan.event_series_list(root=self.root / "missing"), [])

    # ── which list of an edition is this competition ───────────────────────

    def test_jack_and_jill_finds_its_list(self):
        jj, = parse_competition_schedule(
            "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6")
        self.assertTrue(competition_matches_file(jj, Path("JACK_AND_JILL.m3u")))
        self.assertFalse(competition_matches_file(jj, Path("HGR_S_STD.m3u")))
        hgr, = parse_competition_schedule("HGR S STD 2-1")
        self.assertFalse(competition_matches_file(hgr, Path("JACK_AND_JILL.m3u")))

    def test_the_warm_up_list_is_not_the_competition(self):
        self.hgr_2025()
        self.write("DanceConvention 2025/eintanzen_STD.m3u",
                   [self.entry("Warm LW", "LW")])
        spec, = parse_competition_schedule("HGR S STD 2-1")
        files = event_plan.edition_lists(spec, self.root / "DanceConvention 2025")
        self.assertEqual([f.name for f in files], ["HGR_S_STD.m3u"])

    # ── round by round, dance by dance ─────────────────────────────────────

    def test_final_and_preliminary_per_dance(self):
        vr, er, spare = self.hgr_2025()
        spec, = parse_competition_schedule("HGR S STD 2-1")
        rounds = event_plan.event_round_history(
            self.lib, spec, [self.root / "DanceConvention 2025"])
        self.assertEqual(len(rounds), 2)
        final = rounds[1]
        self.assertEqual([e.title for e, _src in final["LW"]], ["ER LW"])
        self.assertEqual([e.title for e, _src in final["QS"]], ["Spare QS"],
                         "the last Quickstep of the list is the final's")
        self.assertEqual([e.title for e, _src in rounds[0]["LW"]],
                         ["VR1 LW", "VR2 LW"])
        self.assertEqual([e.title for e, _src in rounds[0]["QS"]],
                         ["VR1 QS", "VR2 QS", "ER QS"],
                         "the spare only pushes its own dance back")

    def test_every_title_names_the_list_it_came_from(self):
        self.hgr_2025()
        spec, = parse_competition_schedule("HGR S STD 2-1")
        rounds = event_plan.event_round_history(
            self.lib, spec, [self.root / "DanceConvention 2025"])
        _e, src = rounds[1]["LW"][0]
        self.assertEqual(src, "DanceConvention 2025 / HGR_S_STD")

    def test_newer_editions_come_first(self):
        self.hgr_2025()
        old = self.entry("2024 ER LW", "LW")
        self.write("DanceConvention 2024/HGR_S_STD.m3u", [old])
        spec, = parse_competition_schedule("HGR S STD 2-1")
        editions = event_plan.past_editions("danceconvention", root=self.root)
        rounds = event_plan.event_round_history(self.lib, spec, editions)
        self.assertEqual([e.title for e, _src in rounds[1]["LW"]],
                         ["ER LW", "2024 ER LW"])

    def test_dances_outside_the_programme_are_left_out(self):
        """2025's J&J danced Jive as well; 2026's does not."""
        jj_titles = [self.entry("J CC", "CC"), self.entry("J RB", "RB"),
                     self.entry("J LW", "LW"), self.entry("J TG", "TG")]
        jive = MusicEntry(path=Path(r"C:\music\lateincd\J JI (JI 43).mp3"),
                          title="J JI", dance="JI", bpm=43)
        self.lib.entries.append(jive)
        self.write("DanceConvention 2025/JACK_AND_JILL.m3u", jj_titles + [jive])
        spec, = parse_competition_schedule(
            "J & J (LW; TG; CC; RB) VR ZR ER 24 - 12 - 6")
        rounds = event_plan.event_round_history(
            self.lib, spec, [self.root / "DanceConvention 2025"])
        dances = {d for rnd in rounds for d in rnd}
        self.assertEqual(dances, {"LW", "TG", "CC", "RB"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
