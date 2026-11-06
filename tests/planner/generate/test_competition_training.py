"""The competition training list: N heats of the class's dances, then the final.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.generate.test_competition_training -v

One heat is one pass through the dances (a track each); a competition has a
number of heats per dance and a final that may have a different number.
"""
import time
import unittest
from pathlib import Path
from unittest import mock

from planner.generate.warmup import (
    build_competition_training,
    competition_plan,
    competition_rounds,
)
from planner.models import MusicEntry


def _pool(dances, n):
    return [MusicEntry(path=Path(f"C:/m/lateincd/{d}{i}.mp3"), title=f"{d}{i}",
                       dance=d, popularity=n - i)
            for d in dances for i in range(n)]


class CompetitionTrainingTest(unittest.TestCase):
    DANCES = ["SA", "CC", "RB"]

    def build(self, heats, final, rounds=2, n=10, dances=None, **kw):
        return build_competition_training(
            _pool(self.DANCES, n), "Latin", "S", dances or self.DANCES,
            heats, rounds, final, **kw)

    def test_the_heats_of_a_dance_are_played_together_in_each_round(self):
        res = self.build(3, 2)
        self.assertEqual([e.dance for e in res],
                         ["SA"] * 3 + ["CC"] * 3 + ["RB"] * 3
                         + ["SA"] * 2 + ["CC"] * 2 + ["RB"] * 2)

    def test_the_final_can_be_longer_than_the_heats(self):
        self.assertEqual(len(self.build(1, 3)), 3 * 4)

    def test_every_round_before_the_final_has_all_the_heats(self):
        self.assertEqual(len(self.build(2, 1, rounds=4)), 3 * (3 * 2 + 1))

    def test_one_round_is_just_the_final(self):
        self.assertEqual(len(self.build(5, 2, rounds=1)), 3 * 2)

    def test_the_rounds_are_named_and_the_last_is_the_final(self):
        self.assertEqual(competition_rounds(3, 3, 1),
                         [("Runde 1", 3), ("Runde 2", 3), ("Finale", 1)])

    def test_the_plan_gives_each_round_its_heats_and_songs(self):
        self.assertEqual(competition_plan(self.DANCES, 2, 2, 1, 9),
                         [("Runde 1", 2, 6), ("Finale", 1, 3)])

    def test_the_plan_stops_on_the_last_whole_heat(self):
        self.assertEqual(competition_plan(self.DANCES, 3, 2, 1, 7),
                         [("Runde 1", 2, 6)])

    def test_a_track_is_used_once(self):
        res = self.build(3, 2)
        self.assertEqual(len({str(e.path) for e in res}), len(res))

    def test_only_the_ticked_dances_are_built(self):
        res = self.build(2, 1, dances=["SA", "RB"])
        self.assertEqual([e.dance for e in res], ["SA"] * 2 + ["RB"] * 2 + ["SA", "RB"])

    def test_a_dance_that_runs_dry_stops_the_list_on_a_whole_heat(self):
        res = self.build(3, 3, n=2)
        self.assertEqual([e.dance for e in res], ["SA"] * 2 + ["CC"] * 2 + ["RB"] * 2)

    def test_the_heats_of_a_dance_sound_alike(self):
        pool = _pool(["SA"], 10)
        for e in pool:
            e.features = object()
        like = {"SA7": 0.9, "SA5": 0.8}

        def sims(anchor, entries):
            return {str(e.path): like.get(e.title, 0.1) for e in entries}
        with mock.patch("planner.generate.warmup.timbre_similarity", sims):
            res = build_competition_training(pool, "Latin", "S", ["SA"], 3, 1, 3)
        self.assertEqual([e.title for e in res[:3]], ["SA0", "SA7", "SA5"])

    def test_without_timbre_the_most_played_come_first(self):
        pool = _pool(["SA"], 10)
        for e in pool:
            e.features = object()
        with mock.patch("planner.generate.warmup.timbre_similarity",
                        side_effect=AssertionError("not asked")):
            res = build_competition_training(pool, "Latin", "S", ["SA"], 3, 1, 3,
                                             use_timbre=False)
        self.assertEqual([e.title for e in res[:3]], ["SA0", "SA1", "SA2"])

    def test_the_final_takes_the_titles_played_in_finals(self):
        pool = _pool(["SA"], 10)
        for e in pool:
            e.final_plays = 3 if e.title in ("SA8", "SA9") else 0
        res = build_competition_training(pool, "Latin", "S", ["SA"], 2, 2, 1)
        self.assertEqual(res[-1].title, "SA8")

    def test_the_semifinal_takes_the_titles_played_in_semifinals(self):
        pool = _pool(["SA"], 10)
        for e in pool:
            e.semi_plays = 3 if e.title == "SA6" else 0
        res = build_competition_training(pool, "Latin", "S", ["SA"], 1, 3, 1)
        self.assertEqual([e.title for e in res][1], "SA6")

    def test_early_rounds_can_take_fresh_titles_but_not_the_final(self):
        pool = _pool(["SA"], 10)
        res = build_competition_training(pool, "Latin", "S", ["SA"], 2, 2, 2,
                                         use_timbre=False, fresh_ratio=0.5,
                                         fresh_mode="rarely")
        early, final = [e.title for e in res[:2]], [e.title for e in res[2:]]
        self.assertEqual(final, ["SA0", "SA1"])
        self.assertEqual(early[0], "SA2")
        self.assertEqual(early[1], "SA9")

    def test_fresh_means_new_in_the_library_and_rarely_means_any_age(self):
        now = time.time()
        pool = _pool(["SA"], 10)
        for e in pool:
            e.added = now - 5 * 365 * 86400
        pool[8].added = now - 30 * 86400          # SA8: new, not much played
        def heats(mode):
            res = build_competition_training(pool, "Latin", "S", ["SA"], 2, 2, 2,
                                             use_timbre=False, fresh_ratio=0.5,
                                             fresh_mode=mode)
            return [e.title for e in res[:2]]
        self.assertEqual(heats("fresh"), ["SA2", "SA8"])
        self.assertEqual(heats("rarely"), ["SA2", "SA9"])

    def test_a_full_fresh_share_has_no_proven_title_in_the_early_rounds(self):
        pool = _pool(["SA"], 10)
        res = build_competition_training(pool, "Latin", "S", ["SA"], 3, 2, 1,
                                         use_timbre=False, fresh_ratio=1.0,
                                         fresh_mode="rarely")
        self.assertEqual([e.title for e in res[:3]], ["SA9", "SA8", "SA7"])
        self.assertEqual(res[3].title, "SA0")

    def test_no_fresh_share_leaves_the_order_alone(self):
        res = self.build(2, 1, dances=["SA"], use_timbre=False)
        self.assertEqual([e.title for e in res], ["SA1", "SA2", "SA0"])

    def test_the_most_played_tracks_come_first(self):
        res = self.build(1, 1, rounds=1)
        self.assertEqual([e.title for e in res], ["SA0", "CC0", "RB0"])


class OneRecordingPerSongTest(unittest.TestCase):
    """A song is on a training list once, whoever recorded it."""

    @staticmethod
    def pool(*names):
        return [MusicEntry(path=Path(f"C:/m/lateincd/{n}.mp3"), title=n, dance="SA",
                           popularity=20 - i) for i, n in enumerate(names)]

    def build(self, pool, **kw):
        return build_competition_training(pool, "Latin", "S", ["SA"], 2, 1, 2, **kw)

    def test_two_recordings_of_one_title_are_not_in_one_heat(self):
        pool = self.pool("1-04 La Cintura (SB 50)cut", "1-04 La Cintura (SB 50)",
                         "Bamboleo")
        titles = [e.title for e in self.build(pool)]
        self.assertEqual(len(titles), 2)
        self.assertEqual(sum("Cintura" in t for t in titles), 1, titles)

    def test_chroma_twins_under_different_names_are_not_both_played(self):
        pool = self.pool("Alpha Song", "Zulu Tune", "Mango Dance")
        a, b = (str(e.path) for e in pool[:2])
        titles = [e.title for e in self.build(
            pool, twins={a: frozenset({b}), b: frozenset({a})})]
        self.assertEqual(len(titles), 2)
        self.assertEqual(sum(t in ("Alpha Song", "Zulu Tune") for t in titles), 1, titles)

    def test_without_twins_different_names_are_both_played(self):
        pool = self.pool("Alpha Song", "Zulu Tune")
        self.assertEqual(len(self.build(pool)), 2)


if __name__ == "__main__":
    unittest.main()
