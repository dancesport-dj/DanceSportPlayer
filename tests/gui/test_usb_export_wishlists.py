"""🧳 USB export can take the ⭐ wishlists along.

Run:  py -m unittest tests.gui.test_usb_export_wishlists -v

The bundle held the open playlist decks only, never a wishlist. A wishlist is
what the couples asked for, and at the venue it is wanted as much as the
running order. A box in the dialog takes them along, each into its own
numbered folder beside the playlists. Off by default: the bundle stays what
it was unless asked for.
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication, QDialog

from gui.dialogs import UsbExportDialog
from gui.window import main_export
from planner.models import MusicEntry


class DialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, **kw):
        dlg = UsbExportDialog(None, **kw)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_the_box_is_off_by_default(self):
        dlg = self.dialog(n_decks=2, n_wish=1)
        self.assertTrue(dlg._cb_wish.isEnabled())
        self.assertFalse(dlg.include_wishlists())

    def test_ticked_it_takes_the_wishlists(self):
        dlg = self.dialog(n_decks=2, n_wish=1)
        dlg._cb_wish.setChecked(True)
        self.assertTrue(dlg.include_wishlists())

    def test_no_wishlist_with_titles_no_box(self):
        dlg = self.dialog(n_decks=2, n_wish=0)
        self.assertFalse(dlg._cb_wish.isEnabled())
        self.assertFalse(dlg.include_wishlists())

    def test_it_goes_with_the_tournament_day_too(self):
        dlg = self.dialog(n_day=1, n_wish=1, day_selected=True)
        dlg._cb_wish.setChecked(True)
        self.assertTrue(dlg.include_wishlists())

    def test_it_goes_with_dragged_in_files_too(self):
        dlg = self.dialog(n_decks=2, n_wish=1)
        dlg._cb_wish.setChecked(True)
        dlg._cb_dropped.setChecked(True)
        self.assertTrue(dlg.include_wishlists())

    def test_it_is_enough_on_its_own(self):
        dlg = self.dialog(n_wish=1)
        self.assertFalse(dlg._ok.isEnabled())
        dlg._cb_wish.setChecked(True)
        self.assertTrue(dlg._ok.isEnabled())


class ExportTest(unittest.TestCase):
    def host(self, wishes):
        host = mock.Mock()
        host._deckset.decks = []
        host._deckset.day_decks = []
        host._deckset.wishlists = wishes
        host._deckset.warmup_table._row_meta.entries.return_value = []
        host._bundle_jobs_for_decks.return_value = ([], [])
        host._pick_bundle_dir.return_value = (Path("E:/Gala"), True)
        host.deck.side_effect = lambda t: t.deck
        return host

    def wishlist(self, name, entries):
        t = mock.Mock()
        t.deck.name = name
        t._m3u_path = None
        t.wishlist_entries.return_value = entries
        return t

    def run_export(self, host, include):
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.venue_pack.return_value = False
        ask.include_decks.return_value = True
        ask.include_day.return_value = True
        ask.include_party.return_value = False
        ask.include_wishlists.return_value = include
        ask.dropped_paths.return_value = []
        ask.deck_picks.return_value = []
        ask.wish_picks.return_value = []
        with mock.patch.object(main_export, "UsbExportDialog",
                               return_value=ask) as dlg_cls:
            main_export.ExportMixin._export_bundle(host)
        return dlg_cls

    def test_the_dialog_is_told_how_many_wishlists_hold_titles(self):
        song = MusicEntry(path=Path("C:/music/a.mp3"), title="A")
        host = self.host([self.wishlist("Wishes", [song]),
                          self.wishlist("Empty", [])])
        dlg_cls = self.run_export(host, False)
        self.assertEqual(dlg_cls.call_args.kwargs["n_wish"], 1)

    def test_left_off_no_wishlist_is_bundled(self):
        song = MusicEntry(path=Path("C:/music/a.mp3"), title="A")
        host = self.host([self.wishlist("Wishes", [song])])
        self.run_export(host, False)
        host._write_bundle.assert_not_called()

    def test_ticked_each_wishlist_is_a_folder_of_its_own(self):
        song = MusicEntry(path=Path("C:/music/a.mp3"), title="A")
        host = self.host([self.wishlist("Wishes · Gala", [song]),
                          self.wishlist("Empty", [])])
        self.run_export(host, True)
        _bundle, jobs, _skipped = host._write_bundle.call_args.args
        self.assertEqual([title for title, _fn in jobs], ["Wishes - Gala"])
        out = Path(tempfile.mkdtemp(prefix="dp_usb_wish_")) / "Wishes - Gala.m3u"
        written = jobs[0][1](out)
        self.assertIn("a.mp3", Path(written).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
