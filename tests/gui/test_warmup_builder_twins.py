"""🤸 The warm-up worker knows a song filed under two names, as the generator does.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_warmup_builder_twins -v

"01 Be my love - Werner Tauber" and "01 - Be My Love - SF 30" share no use key,
so only the library's title twins (planner.music.title_twins) tie them. The
tournament generator merges those with the Chroma twins; the class warm-up,
the competition training and the party list must not play the song twice.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_warmup_twins_"))

from PySide6.QtWidgets import QApplication

from gui.workers import WarmupBuilder
from planner.models import MusicEntry
from planner.music.title_twins import title_twins

_app = QApplication.instance() or QApplication([])

TWINS = ("01 Be my love - Werner Tauber", "01 - Be My Love - SF 30")


def _entries():
    names = (*TWINS, "Moon River (SF 30)", "Charade (SF 29)")
    return [MusicEntry(path=Path(f"C:/m/standardcd/{n}.mp3"), title=n, dance="SF",
                       bpm=29, popularity=10 - i) for i, n in enumerate(names)]


class WarmupBuilderTwinsTest(unittest.TestCase):

    def build(self, mode, params):
        entries = _entries()
        worker = WarmupBuilder(entries, mode, params, None, cache=None,
                               title_twins=lambda: title_twins(entries))
        out, errors = [], []
        worker.done.connect(out.append)
        worker.error.connect(errors.append)
        worker.run()
        self.assertEqual(errors, [])
        return [e.title for e in out[0]]

    def assert_once(self, titles):
        self.assertEqual(sum(t in TWINS for t in titles), 1, titles)

    def test_a_party_list_plays_the_song_once(self):
        self.assert_once(self.build("etds", {"include_latin": False}))

    def test_a_class_warmup_plays_the_song_once(self):
        self.assert_once(self.build("class", {
            "style": "Standard", "dance_class": "S", "fresh_ratio": 0}))


if __name__ == "__main__":
    unittest.main()
