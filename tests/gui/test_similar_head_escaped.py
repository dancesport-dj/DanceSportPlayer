"""Titles in the Similar-Tracks heading are shown as typed (review s. 4).

The heading is a rich-text QLabel; a title like "Tango <3 Remix" or one holding
"<i>" went into it unescaped and was read as markup.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_simhead_"))

from PySide6.QtWidgets import QApplication

from gui.dialogs.similar_dialog import SimilarTracksDialog
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


def _entry(title):
    return MusicEntry(path=Path(rf"C:\music\tanzcds\standardcd\{title[:6]}.mp3"),
                      title=title, dance="LW", bpm=29)


class SimilarHeadEscapedTest(unittest.TestCase):

    def head(self, **kw):
        dlg = SimilarTracksDialog(kw.pop("source", None), [(0.9, _entry("other"))],
                                  **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg._head.text()

    def test_a_source_title_is_escaped(self):
        text = self.head(source=_entry("Tango <i>3</i> & more"))
        self.assertIn("Tango &lt;i&gt;3&lt;/i&gt; &amp; more", text)
        self.assertNotIn("<i>", text)

    def test_a_history_title_is_escaped(self):
        text = self.head(history_title="Waltz <b>R1</b>")
        self.assertIn("Waltz &lt;b&gt;R1&lt;/b&gt;", text)


if __name__ == "__main__":
    unittest.main()
