"""A tooltip built from a tag, a playlist line or a pack field shows as text.

Run:  py -m unittest tests.gui.test_plain_tooltips -v

Qt reads a tooltip that looks like markup as markup, and an `<img src>` in it
opens that path (an SMB login for a UNC path). The comment tag, the Custom
column and a playlist line naming a missing file all reach a tooltip as typed.
A LOCAL png stands in for the share: same resource loader, and a loaded image
makes the label taller. Security audit run-2 #3.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_plain_tips_"))

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QLabel

from dancesport_planner import RoundConfig
from gui.library_browser import LIB_COL_COMMENT, LIB_COL_CUSTOM, LIB_COL_FILE, LibraryBrowser
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_TMP = tempfile.mkdtemp(prefix="dp_plain_tips_png_")
PNG = os.path.join(_TMP, "probe.png").replace("\\", "/")
_img = QImage(300, 400, QImage.Format.Format_RGB32)
_img.fill(QColor("red"))
_img.save(PNG)

BAIT = f'Cha Cha <img src="{PNG}"> (Remix)'


def shown_height(tip: str) -> int:
    """How tall Qt draws this tooltip text."""
    lbl = QLabel(tip)
    lbl.adjustSize()
    return lbl.sizeHint().height()


def _entry():
    # A playlist line can name a path that is not on disk, so the path is as
    # free as the tags are.
    return MusicEntry(path=Path(f'C:/nowhere/{BAIT}.mp3'), title="Lady Hear Me Tonight",
                      dance="LW", bpm=29, tag_comment=BAIT, custom=BAIT)


class CanaryTest(unittest.TestCase):

    def test_the_bait_is_tall_as_a_raw_tooltip(self):
        # If this stops holding, the tests below prove nothing.
        self.assertGreater(shown_height(BAIT), 300)


class DeckTooltipTest(unittest.TestCase):

    def test_no_cell_of_the_row_shows_the_bait_as_markup(self):
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        entry = _entry()
        table.load({"Final": [[entry]]}, ["LW"],
                   [RoundConfig(name="Final", heats=1, tier="final")], "S",
                   play_cb=lambda *_: None, suggester=None,
                   use_timbre=False, style="Standard")
        row = next(r for r, m in enumerate(table._row_meta) if m and m.entry is entry)
        checked = 0
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item is not None and item.toolTip():
                checked += 1
                with self.subTest(col=col):
                    self.assertLess(shown_height(item.toolTip()), 200)
        self.assertGreaterEqual(checked, 3)   # title, comment, custom at least


class LibraryTooltipTest(unittest.TestCase):

    def test_comment_custom_and_file_cells(self):
        pane = LibraryBrowser()
        self.addCleanup(reap_widget, pane)
        pane.set_entries([_entry()])
        for col in (LIB_COL_COMMENT, LIB_COL_CUSTOM, LIB_COL_FILE):
            with self.subTest(col=col):
                tip = pane.cell_tooltip(0, col)
                self.assertTrue(tip)
                self.assertLess(shown_height(tip), 200)


if __name__ == "__main__":
    unittest.main()
