#!/usr/bin/env python3
"""A replacement 🔁 Check duplicates takes from the wishlist leaves the wishlist.

Run:  py -m unittest tests.gui.test_duplicate_wishlist_take -v

The replacement picker offers the wishlist titles (07313a2), but a title taken
from there into a deck stayed in the wishlist too, so the next check flagged it
wishlist↔deck. Marcel chose that taking a title moves it, the way dragging it
out of the wishlist already does.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_wish_take_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from tests.gui.test_duplicate_check_scope import _Status, _Win, _waltz  # noqa: E402
from tests.gui.test_duplicate_remove import _entries  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class DuplicateWishlistTakeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _Win()
        self.win.statusBar = lambda: _Status()
        self.addCleanup(reap_widget, self.win)
        self.a, self.b, self.c = _waltz("Alpha"), _waltz("Beta"), _waltz("Gamma")
        self.deck_a, self.deck_e = self.win._decks[0], self.win._decks[4]
        self.wish = self.win._wishlists[0]
        self.win.fill_deck(self.deck_a, [self.a, self.b])

    def _slot(self, table, entry) -> int:
        self.win._deck_dup_report()
        return next(i for i, (t, _r, e) in enumerate(self.win._dup_slots)
                    if t is table and e is entry)

    def test_a_wishlist_title_taken_into_a_deck_leaves_the_wishlist(self):
        self.win.fill_deck(self.deck_e, [self.c, self.a])
        self.win.fill_list(self.wish, [_waltz("Delta"), _waltz("Epsilon")])
        # The picker hands back the library's entry: the same file, another object.
        picked = _waltz("Delta")
        self.win._apply_dup_resolutions([(self._slot(self.deck_e, self.a), picked)])
        self.assertEqual(_entries(self.deck_e), [self.c, picked])
        self.assertEqual([e.title for e in self.wish.wishlist_entries()], ["Epsilon"])

    def test_a_title_from_elsewhere_leaves_the_wishlist_alone(self):
        self.win.fill_deck(self.deck_e, [self.c, self.a])
        self.win.fill_list(self.wish, [_waltz("Delta"), _waltz("Epsilon")])
        self.win._apply_dup_resolutions([(self._slot(self.deck_e, self.a),
                                          _waltz("Omega"))])
        self.assertEqual([e.title for e in self.wish.wishlist_entries()],
                         ["Delta", "Epsilon"])

    def test_a_replacement_placed_in_the_wishlist_stays_there(self):
        self.win.fill_list(self.wish, [self.a, _waltz("Delta")])
        wish_a = self.wish.wishlist_entries()[0]
        self.win._apply_dup_resolutions([(self._slot(self.wish, wish_a),
                                          _waltz("Omega"))])
        self.assertEqual([e.title for e in self.wish.wishlist_entries()],
                         ["Omega", "Delta"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
