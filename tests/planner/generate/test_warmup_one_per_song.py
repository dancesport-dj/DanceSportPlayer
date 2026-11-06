"""Class warm-up and ETDS party list: a song is on the list once.

Run:  .venv/Scripts/python.exe -m unittest tests.planner.generate.test_warmup_one_per_song -v
"""
import unittest
from pathlib import Path

from planner.generate.warmup import build_class_warmup, build_warmup_playlist
from planner.models import MusicEntry


def _pool(*names, dance="SA"):
    return [MusicEntry(path=Path(f"C:/m/lateincd/{n}.mp3"), title=n, dance=dance,
                       popularity=20 - i) for i, n in enumerate(names)]


class ClassWarmupTest(unittest.TestCase):

    def build(self, pool, **kw):
        return build_class_warmup(pool, "Latin", "S", fresh_ratio=0, **kw)

    def test_two_recordings_of_one_title_are_played_once(self):
        pool = _pool("1-04 La Cintura (SB 50)cut", "1-04 La Cintura (SB 50)", "Bamboleo")
        titles = [e.title for e in self.build(pool)]
        self.assertEqual(sum("Cintura" in t for t in titles), 1, titles)
        self.assertEqual(len(titles), 2)

    def test_chroma_twins_under_different_names_are_played_once(self):
        pool = _pool("Alpha Song", "Zulu Tune", "Mango Dance")
        a, b = (str(e.path) for e in pool[:2])
        titles = [e.title for e in self.build(
            pool, twins={a: frozenset({b}), b: frozenset({a})})]
        self.assertEqual(sum(t in ("Alpha Song", "Zulu Tune") for t in titles), 1, titles)


class EtdsWarmupTest(unittest.TestCase):

    def test_two_recordings_of_one_title_are_played_once(self):
        pool = _pool("07 De Hombre A Mujer (CC 31)", "1-06 De hombre a mujerT32",
                     "Bamboleo", dance="CC")
        titles = [e.title for e in build_warmup_playlist(pool, include_standard=False)]
        self.assertEqual(sum("ombre" in t for t in titles), 1, titles)

    def test_chroma_twins_under_different_names_are_played_once(self):
        pool = _pool("Alpha Song", "Zulu Tune", "Mango Dance", dance="CC")
        a, b = (str(e.path) for e in pool[:2])
        titles = [e.title for e in build_warmup_playlist(
            pool, include_standard=False,
            twins={a: frozenset({b}), b: frozenset({a})})]
        self.assertEqual(sum(t in ("Alpha Song", "Zulu Tune") for t in titles), 1, titles)


if __name__ == "__main__":
    unittest.main()
