#!/usr/bin/env python3
"""🔁 Check duplicates can take a copy out instead of replacing it.

Run:  py -m unittest tests.gui.test_duplicate_remove -v

Marcel: "add check duplicates option to remove from left or right". A song
shared by two lists could only be kept or replaced; now its row also offers
🗑 Remove from either list, and a title doubled inside one list can be removed
there too. A deck keeps its heat slot (emptied, as the Del key leaves it); a
wishlist loses the row.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_remove_"))

from PySide6.QtWidgets import QApplication, QComboBox, QMessageBox  # noqa: E402

from gui.duplicate_dialog import DuplicateResolveDialog  # noqa: E402
from tests.gui.test_duplicate_check_scope import _Status, _Win, _waltz  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


def _entries(table) -> list:
    return [m.entry for _r, m in table._row_meta.numbered()]


class DuplicateRemoveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _Win()
        self.win.statusBar = lambda: _Status()
        self.addCleanup(reap_widget, self.win)
        self.a, self.b, self.c = _waltz("Alpha"), _waltz("Beta"), _waltz("Gamma")
        self.deck_a, self.deck_e = self.win._decks[0], self.win._decks[4]
        self.win.fill_deck(self.deck_a, [self.a, self.b])
        self.win.fill_deck(self.deck_e, [self.c, self.a])

    def _dialog(self) -> DuplicateResolveDialog:
        dlg = DuplicateResolveDialog(self.win._deck_dup_report(), self.win,
                                     pick_fn=lambda e: self.fail("no pick expected"))
        self.addCleanup(reap_widget, dlg)
        return dlg

    @staticmethod
    def _choose(dlg, text: str):
        for combo in dlg.findChildren(QComboBox):
            i = combo.findText(text)
            if i >= 0:
                combo.setCurrentIndex(i)
                combo.activated.emit(i)
                return
        raise AssertionError(f"no action {text!r} in {[c.itemText(i) for c in dlg.findChildren(QComboBox) for i in range(c.count())]}")

    def _apply(self, dlg):
        with mock.patch.object(QMessageBox, "warning", lambda *a: self.fail(a[2])), \
                mock.patch.object(QMessageBox, "information", lambda *a: self.fail(a[2])):
            dlg._on_apply()
        self.win._apply_dup_resolutions(dlg.resolutions)

    def test_remove_from_the_right_list(self):
        dlg = self._dialog()
        self._choose(dlg, "🗑  Remove from Deck E")
        self._apply(dlg)
        self.assertEqual(_entries(self.deck_a), [self.a, self.b])
        self.assertEqual(_entries(self.deck_e), [self.c])

    def test_remove_from_the_left_list(self):
        dlg = self._dialog()
        self._choose(dlg, "🗑  Remove from Deck A")
        self._apply(dlg)
        self.assertEqual(_entries(self.deck_a), [self.b])
        self.assertEqual(_entries(self.deck_e), [self.c, self.a])

    def test_a_deck_keeps_the_emptied_slot(self):
        rows = self.deck_e.rowCount()
        dlg = self._dialog()
        self._choose(dlg, "🗑  Remove from Deck E")
        self._apply(dlg)
        self.assertEqual(self.deck_e.rowCount(), rows)

    def test_remove_from_a_wishlist_drops_the_row(self):
        wl = self.win._wishlists[0]
        self.win.fill_list(wl, [self.c, _waltz("Delta"), self.b])
        rows = wl.rowCount()
        dlg = self._dialog()
        self._choose(dlg, "🗑  Remove from Wishlist")
        self._apply(dlg)
        self.assertEqual([e.title for e in wl.wishlist_entries()], ["Gamma", "Delta"])
        self.assertEqual(wl.rowCount(), rows - 1)

    def test_a_title_doubled_in_one_list_can_be_removed(self):
        wl = self.win._wishlists[0]
        again = _waltz("Omega", folder="other")
        self.win.fill_list(wl, [_waltz("Omega"), _waltz("Delta"), again])
        dlg = self._dialog()
        combos = [c for c in dlg.findChildren(QComboBox) if c.findText("🗑  Remove") >= 0]
        self.assertEqual(len(combos), 2)            # one per copy
        combos[1].setCurrentIndex(combos[1].findText("🗑  Remove"))
        combos[1].activated.emit(combos[1].currentIndex())
        self._apply(dlg)
        self.assertEqual([e.title for e in wl.wishlist_entries()], ["Omega", "Delta"])
        self.assertEqual(str(wl.wishlist_entries()[0].path), str(_waltz("Omega").path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
