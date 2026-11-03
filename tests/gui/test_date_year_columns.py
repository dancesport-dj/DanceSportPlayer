"""Created, Modified and Year in the library pane: appended last, hidden until
ticked, and filled from the entry (creation time, modification time, tag year)."""
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_datecols_"))

from PySide6.QtWidgets import QApplication

from gui.library_browser import (
    LIB_COL_ADDED,
    LIB_COL_CREATED,
    LIB_COL_MODIFIED,
    LIB_COL_YEAR,
    LibraryBrowser,
)
from planner.models import MusicEntry
from planner.music.library import library_mp3s, listed_mtimes
from tests.qt_test_support import reap_widget


class DateYearColumnsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def browser(self, entry):
        lb = LibraryBrowser()
        self.addCleanup(reap_widget, lb)
        lb.resize(1000, 400)
        lb.show()
        lb.set_entries([entry])
        self.app.processEvents()
        return lb

    def test_created_shows_by_default_and_added_does_not(self):
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a"))
        hidden = lb.hidden_columns()
        self.assertNotIn(LIB_COL_CREATED, hidden)
        self.assertIn(LIB_COL_ADDED, hidden)   # Added: the date the library first saw the file

    def test_they_come_last_and_start_hidden(self):
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a"))
        self.assertEqual((LIB_COL_CREATED, LIB_COL_MODIFIED, LIB_COL_YEAR), (16, 17, 18))  # pinned: saved layouts index by number
        self.assertEqual(lb._table.columnCount(), 19)
        for c in (LIB_COL_MODIFIED, LIB_COL_YEAR):
            self.assertIn(c, lb.hidden_columns())

    def test_the_cells_show_the_entry(self):
        created = datetime(2025, 3, 4, 17, 30).timestamp()
        modified = datetime(2026, 1, 2, 9, 5).timestamp()
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a", year=1998,
                                     created=created, modified=modified,
                                     added=created + 86400))
        t = lb._table
        self.assertEqual(t.item(0, LIB_COL_CREATED).text(), "2025-03-04 17:30")
        self.assertEqual(t.item(0, LIB_COL_ADDED).text(), "2025-03-05 17:30")
        self.assertEqual(t.item(0, LIB_COL_MODIFIED).text(), "2026-01-02 09:05")
        self.assertEqual(t.item(0, LIB_COL_YEAR).text(), "1998")

    def test_date_only_drops_the_hour_from_all_three_columns(self):
        created = datetime(2025, 3, 4, 17, 30).timestamp()
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a", created=created,
                                     modified=created, added=created))
        lb.set_date_only(True)
        t = lb._table
        for c in (LIB_COL_ADDED, LIB_COL_CREATED, LIB_COL_MODIFIED):
            self.assertEqual(t.item(0, c).text(), "2025-03-04")
        lb.set_date_only(False)
        self.assertEqual(t.item(0, LIB_COL_CREATED).text(), "2025-03-04 17:30")

    def test_the_column_menu_offers_date_only_and_tells_the_window(self):
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a"))
        seen = []
        lb.dateOnlyChanged.connect(seen.append)
        act = [a for a in lb.build_column_menu().actions()
               if a.text().startswith("Date only")]
        self.assertEqual(len(act), 1)
        act[0].trigger()
        self.assertEqual(seen, [True])
        self.assertTrue(lb.date_only())

    def test_a_new_fill_keeps_date_only(self):
        created = datetime(2025, 3, 4, 17, 30).timestamp()
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a", created=created))
        lb.set_date_only(True)
        lb.set_entries([MusicEntry(path=Path("b.mp3"), title="b", created=created)])
        self.app.processEvents()
        self.assertEqual(lb._table.item(0, LIB_COL_CREATED).text(), "2025-03-04")

    def test_unknown_values_are_blank(self):
        lb = self.browser(MusicEntry(path=Path("a.mp3"), title="a"))
        for c in (LIB_COL_CREATED, LIB_COL_MODIFIED, LIB_COL_YEAR):
            self.assertEqual(lb._table.item(0, c).text(), "")

    def test_the_listing_hands_over_the_creation_time(self):
        # The whole-library view lists folders instead of walking, and used to
        # leave Created empty.
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.mp3"
            f.write_bytes(b"")
            created = {}
            listed_mtimes([d], created)
            self.assertGreater(created[str(f)], 0)

    def test_the_walk_hands_over_the_mtime(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "x.mp3"
            f.write_bytes(b"")
            os.utime(f, (1_700_000_000, 1_700_000_000))
            mtimes = {}
            library_mp3s(Path(d), mtimes)
            self.assertEqual(mtimes[str(f)], 1_700_000_000)


if __name__ == "__main__":
    unittest.main()
