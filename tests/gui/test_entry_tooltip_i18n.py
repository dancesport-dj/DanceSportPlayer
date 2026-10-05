"""The rich track tooltip in German.

Run:  py -m unittest tests.gui.test_entry_tooltip_i18n -v

`_entry_tooltip` builds one HTML block from the track's data, so the Qt text
hook sees a whole tooltip that is never a catalog key: hovering a title on a
German floor read "Similarity: 91.0%", "In 4 of your playlists", "Played in:".
Its labels go through i18n.t where the block is built.
"""
import os
import tempfile
import unittest
from pathlib import Path

from planner import i18n
from planner.models import MusicEntry


def _tooltip(*args, **kw):
    # gui.common resolves the state files at import time — keep the import at
    # TEST time (see test_drop_check.py).
    os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_tip_"))
    from gui.common import _entry_tooltip
    return _entry_tooltip(*args, **kw)


def _entry():
    e = MusicEntry(path=Path(r"C:\music\Sway.mp3"), title="Sway", dance="CC", bpm=31,
                   popularity=4, is_instrumental=True, is_xmas=True)
    e.classes_ok = ["B", "A"]
    e.class_plays = {"S": 3, "C": 1}
    return e


class GermanTooltipTest(unittest.TestCase):

    def setUp(self):
        i18n.set_active("de")
        self.addCleanup(i18n.set_active, i18n.DEFAULT_LANGUAGE)

    def test_labels_read_german(self):
        tip = _tooltip(_entry(), 0.91, "Similarity")
        for german in ("Instrumental", "🎄 Weihnachten", "Ähnlichkeit: <b>91.0%</b>",
                       "Klassen: B, A", "In 4 deiner Playlists", "Gespielt in: S×3 · C×1"):
            self.assertIn(german, tip)
        for english in ("Similarity", "Christmas", "Classes:", "of your playlists",
                        "Played in:"):
            self.assertNotIn(english, tip)

    def test_past_lists(self):
        e = _entry()
        e.replay_sources = [f"list {i}" for i in range(10)]
        tip = _tooltip(e)
        self.assertIn("In diesen passenden früheren Listen:", tip)
        self.assertIn("… +2 weitere", tip)

    def test_the_similar_window_labels(self):
        self.assertIn("Treffer: <b>", _tooltip(_entry(), 0.5, "Match"))
        self.assertIn("Zusammen gespielt: <b>", _tooltip(_entry(), 0.5, "Played together"))


class EnglishUnchangedTest(unittest.TestCase):

    def test_labels(self):
        tip = _tooltip(_entry(), 0.91, "Similarity")
        for english in ("instrumental", "🎄 Christmas", "Similarity: <b>91.0%</b>",
                        "Classes: B, A", "In 4 of your playlists", "Played in: S×3 · C×1"):
            self.assertIn(english, tip)


if __name__ == "__main__":
    unittest.main()
