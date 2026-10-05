#!/usr/bin/env python3
"""🔁 Check duplicates stays open beside the decks while files are checked.

Run:  py -m unittest tests.gui.test_duplicate_dialog_modeless -v

Marcel: "i want the check duplicates dialog to be possible to let it open and
work on playlist so i can look in it, currently it blocks the windows below".
And then: "dann erlaube es nur in dem unterfenster wo man von außen dateien
reinzieht nicht bei der open playlist sektion". The dialog ran through exec(),
so nothing below it could be touched. Now only 🎚️ Open playlists blocks — its
report names each copy by its deck row. The tabs for dragged-in files leave
the decks usable, and a deck changed meanwhile must not fool ✅ Apply: it has
to find the copy where it sits now, and leave alone a row that holds another
title by then.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_modeless_"))

from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.duplicate_dialog import DuplicateResolveDialog  # noqa: E402
from gui.main_dupes import DuplicateCheckMixin  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.library import MusicLibrary  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from planner.suggester import PlaylistSuggester  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _waltz(name: str) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\standardcd\{name} (LW 29).mp3"),
                      title=name, dance="LW", bpm=29)


class _Win(QWidget, DuplicateCheckMixin):
    """The main window as far as the duplicate check reaches: one deck."""

    def __init__(self, songs):
        super().__init__()
        self._settings = {"app_mode": "full"}
        self._cache = None
        self._lib = MusicLibrary()
        self._lib.entries += songs
        self.deck_table = PlaylistTable()
        self.deck_table.setParent(self)
        heats = [[s] for s in songs]
        self.deck_table.load(
            {"Vorrunde": heats}, ["LW"],
            [RoundConfig(name="Vorrunde", heats=len(heats), tier="early")], "D",
            play_cb=None, suggester=PlaylistSuggester(self._lib),
            use_timbre=False)
        self._wishlists = []
        self.status = mock.Mock()

    def _dup_check_tables(self):
        return [self.deck_table]

    def _deck_report_name(self, table):
        return "A Deck"

    def statusBar(self):
        return self.status

    def _pick_replacement(self, entry):
        return None

    def _check_dropped_duplicates(self, paths, progress_cb=None):
        return {"within": [], "cross": []}

    def _play_or_stop(self, path):
        pass

    def _seek(self, ms):
        pass


def _entries(table) -> list:
    return [m.entry for _r, m in table._row_meta.numbered()]


class DuplicateDialogModelessTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.a, self.b, self.new = _waltz("Alpha"), _waltz("Beta"), _waltz("New")
        self.win = _Win([self.a, self.b])
        self.addCleanup(reap_widget, self.win)

    def _open(self) -> DuplicateResolveDialog:
        def blocking(dlg):
            self.fail("the check ran the dialog modally through exec()")
        with mock.patch.object(DuplicateResolveDialog, "exec", blocking):
            self.win._check_duplicates()
        dlgs = self.win.findChildren(DuplicateResolveDialog)
        self.assertEqual(len(dlgs), 1)
        return dlgs[0]

    def test_the_open_playlists_tab_blocks_the_decks(self):
        dlg = self._open()
        self.addCleanup(dlg.reject)
        self.assertTrue(dlg.isVisible())
        self.assertIs(dlg._tabs.currentWidget(), dlg._decks_tab_w)
        self.assertIs(QApplication.activeModalWidget(), dlg)

    def test_the_drag_in_tabs_leave_the_decks_usable(self):
        dlg = self._open()
        self.addCleanup(dlg.reject)
        for tab in (dlg._drop_tab_w, dlg._ref_tab_w):
            self.assertIsNotNone(tab)
            dlg._tabs.setCurrentWidget(tab)
            self.assertTrue(dlg.isVisible())
            self.assertIsNone(QApplication.activeModalWidget())

    def test_back_on_open_playlists_it_blocks_again(self):
        dlg = self._open()
        self.addCleanup(dlg.reject)
        dlg._tabs.setCurrentWidget(dlg._drop_tab_w)
        dlg._tabs.setCurrentWidget(dlg._decks_tab_w)
        self.assertTrue(dlg.isVisible())
        self.assertIs(QApplication.activeModalWidget(), dlg)

    def test_a_second_check_brings_the_open_one_back(self):
        dlg = self._open()
        self.addCleanup(dlg.reject)
        dlg._tabs.setCurrentWidget(dlg._drop_tab_w)   # decks usable meanwhile
        self._open()
        self.assertIs(self.win.findChildren(DuplicateResolveDialog)[0], dlg)

    def test_closing_it_frees_it(self):
        self._open().reject()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.assertEqual(self.win.findChildren(DuplicateResolveDialog), [])

    def test_accepting_applies_its_replacements(self):
        dlg = self._open()
        dlg.resolutions = [(0, self.new)]
        dlg.accept()
        self.assertEqual(_entries(self.win.deck_table), [self.new, self.b])

    def test_apply_follows_a_copy_that_moved(self):
        self.win._deck_dup_report()                    # slot 0 = Alpha, slot 1 = Beta
        rows = [r for r, _m in self.win.deck_table._row_meta.numbered()]
        meta = self.win.deck_table._row_meta
        meta[rows[0]].entry, meta[rows[1]].entry = self.b, self.a   # moved meanwhile
        self.win._apply_dup_resolutions([(0, self.new)])
        self.assertEqual(_entries(self.win.deck_table), [self.b, self.new])

    def test_apply_leaves_a_copy_that_is_gone(self):
        self.win._deck_dup_report()
        rows = [r for r, _m in self.win.deck_table._row_meta.numbered()]
        other = _waltz("Other")
        self.win.deck_table._row_meta[rows[0]].entry = other   # regenerated meanwhile
        self.win._apply_dup_resolutions([(0, self.new)])
        self.assertEqual(_entries(self.win.deck_table), [other, self.b])


if __name__ == "__main__":
    unittest.main(verbosity=2)
