#!/usr/bin/env python3
"""A replacement picked in 🔁 Check duplicates must not be a duplicate itself.

Run:  py -m unittest tests.gui.test_duplicate_replacement_pick -v

Marcel: "if similar dialog for replacement opens make sure that if we coming from
duplicates check it does not show titles that are in other open lists.
otherwise it is a ping pong game". The Similar-tracks picker offered titles
already in the checked lists, so the next check flagged the replacement. From
the duplicate check it now leaves out everything the check covers but the
wishlists (the ⭐ option picks from them), and the replacements already
chosen in the open dialog.
"""

import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_dup_pick_"))

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from tests.gui.test_duplicate_check_scope import _Win, _waltz  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class _PickWin(_Win):
    def current_wishlist_paths(self):
        return set()

    def _play_or_stop(self, path):
        pass

    def _seek(self, ms):
        pass


class DuplicateReplacementPickTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.win = _PickWin()
        self.addCleanup(reap_widget, self.win)
        self.a, self.b = _waltz("Alpha"), _waltz("Beta")
        self.win.fill_deck(self.win._decks[0], [self.a, self.b])
        self.win.fill_deck(self.win._decks[4], [_waltz("Gamma")])
        self.win.fill_list(self.win._wishlists[0], [_waltz("Delta")])
        self.offered = None

    def _pick(self, results, fn=None):
        self.win._lib.similar_tracks = lambda *a, **k: results

        def capture(entry, res, *a, **k):
            self.offered = [e.title for _s, e in res]
            self.hide_fn = k.get("hide_fn")
            dlg = mock.Mock()
            dlg.exec.return_value = 0
            return dlg
        with mock.patch("gui.main_dupes.SimilarTracksDialog", side_effect=capture):
            return (fn or self.win._pick_dup_replacement)(self.a)

    def test_titles_in_the_decks_are_not_offered(self):
        results = [(0.9, _waltz("Gamma", folder="other")),   # in deck E
                   (0.7, _waltz("Beta", folder="other")),     # in deck A itself
                   (0.6, _waltz("Zeta"))]
        self._pick(results)
        self.assertEqual(self.offered, ["Zeta"])

    def test_wishlist_titles_stay_on_offer(self):
        # Marcel: "wenn ich die option aus wishlist auswähle sollen natürlich
        # nicht die wishlist einträge entfernt werden" — the wishlists are
        # where a replacement comes from.
        self._pick([(0.8, _waltz("Delta")), (0.6, _waltz("Zeta"))])
        self.assertEqual(self.offered, ["Delta", "Zeta"])
        self.assertEqual([e.title for _s, e in self.hide_fn([(0.8, _waltz("Delta"))])],
                         ["Delta"])

    def test_the_window_hides_them_when_it_ranks_anew(self):
        # It ranks again as it opens ("combined") and on every method switch.
        self._pick([(0.6, _waltz("Zeta"))])
        fresh = [(0.9, _waltz("Gamma", folder="other")), (0.6, _waltz("Zeta"))]
        self.assertEqual([e.title for _s, e in self.hide_fn(fresh)], ["Zeta"])

    def test_a_replacement_chosen_in_the_dialog_is_not_offered_again(self):
        dlg = mock.Mock()
        dlg.pending_replacements.return_value = [_waltz("Zeta")]
        self.win._dup_dlg = dlg
        self._pick([(0.7, _waltz("Zeta")), (0.6, _waltz("Eta"))])
        self.assertEqual(self.offered, ["Eta"])

    def test_nothing_left_says_why(self):
        with mock.patch.object(QMessageBox, "information") as info:
            self.assertIsNone(self._pick([(0.9, _waltz("Gamma", folder="other"))]))
        self.assertIsNone(self.offered)
        self.assertIn("already in an open playlist", info.call_args[0][2])

    def test_the_music_check_picker_still_offers_everything(self):
        self._pick([(0.9, _waltz("Gamma", folder="other")), (0.6, _waltz("Zeta"))],
                   fn=self.win._pick_replacement)
        self.assertEqual(self.offered, ["Gamma", "Zeta"])
        self.assertIsNone(self.hide_fn)


if __name__ == "__main__":
    unittest.main(verbosity=2)
