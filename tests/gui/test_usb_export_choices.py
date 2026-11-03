#!/usr/bin/env python3
"""🧳 USB export: tick what goes along, in any combination, the party list too.

Run:  py -m unittest tests.gui.test_usb_export_choices -v

Marcel's list, 7.4: "Add an option to export the party playlist. Replace the
either/or choice with checkboxes so combinations are possible (e.g. playlist +
wishlist, party + wishlist)." The 📦 venue pack is no bundle, so it combines with
nothing: it stays a choice of its own, as a button.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QRadioButton

from gui.dialogs import UsbExportDialog
from gui.window import main_export
from planner.models import MusicEntry

SONG = MusicEntry(path=Path("C:/music/a.mp3"), title="A")


class DialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, **kw):
        dlg = UsbExportDialog(None, **kw)
        self.addCleanup(dlg.deleteLater)
        return dlg

    @staticmethod
    def picked(dlg):
        return [name for name, on in (("decks", dlg.include_decks()),
                                      ("day", dlg.include_day()),
                                      ("party", dlg.include_party()),
                                      ("wish", dlg.include_wishlists())) if on]

    def test_nothing_is_either_or_any_more(self):
        self.assertEqual(self.dialog(n_decks=1).findChildren(QRadioButton), [])

    def test_a_plain_export_stays_what_it_was(self):
        """Every deck with the 📅 day, as 'All open playlists' was."""
        dlg = self.dialog(n_decks=2, n_day=1, n_party=9, n_wish=1)
        self.assertEqual(self.picked(dlg), ["decks", "day"])

    def test_the_open_day_tab_means_the_day_alone(self):
        dlg = self.dialog(n_decks=2, n_day=1, day_selected=True)
        self.assertEqual(self.picked(dlg), ["day"])

    def test_playlist_and_wishlist(self):
        dlg = self.dialog(n_decks=2, n_wish=1)
        dlg._cb_wish.setChecked(True)
        self.assertEqual(self.picked(dlg), ["decks", "wish"])

    def test_party_and_wishlist(self):
        dlg = self.dialog(n_decks=2, n_party=9, n_wish=1)
        dlg._cb_decks.setChecked(False)
        dlg._cb_party.setChecked(True)
        dlg._cb_wish.setChecked(True)
        self.assertEqual(self.picked(dlg), ["party", "wish"])

    def test_a_lone_party_list_is_ticked_at_once(self):
        dlg = self.dialog(n_party=9)
        self.assertEqual(self.picked(dlg), ["party"])
        self.assertTrue(dlg._ok.isEnabled())

    def test_each_playlist_with_titles_has_its_own_tick(self):
        dlg = self.dialog(n_decks=3, deck_names=["A", "B", "C"])
        ticks = dlg._deck_ticks
        self.assertEqual([t.text() for t in ticks], ["A", "B", "C"])
        ticks[1].setChecked(False)
        self.assertEqual(dlg.deck_picks(), [0, 2])
        for t in ticks:
            t.setChecked(False)
        self.assertFalse(dlg.include_decks())

    def test_wishlists_can_be_picked_too(self):
        dlg = self.dialog(n_wish=2, wish_names=["W1", "W2"])
        dlg._cb_wish.setChecked(True)
        dlg._wish_ticks[0].setChecked(False)
        self.assertEqual(dlg.wish_picks(), [1])
        self.assertTrue(dlg.include_wishlists())

    def test_what_is_empty_cannot_be_ticked(self):
        dlg = self.dialog(n_decks=1)
        for box in (dlg._cb_day, dlg._cb_party, dlg._cb_wish):
            self.assertFalse(box.isEnabled())

    def test_the_party_caption_counts_its_titles(self):
        self.assertIn("(1 title)", self.dialog(n_party=1)._cb_party.text())
        self.assertIn("(9 titles)", self.dialog(n_party=9)._cb_party.text())

    def test_nothing_ticked_exports_nothing(self):
        dlg = self.dialog(n_decks=1)
        self.assertTrue(dlg._ok.isEnabled())
        dlg._cb_decks.setChecked(False)
        self.assertFalse(dlg._ok.isEnabled())

    def test_the_dragged_in_box_alone_needs_files(self):
        dlg = self.dialog(n_decks=1)
        dlg._cb_decks.setChecked(False)
        dlg._cb_dropped.setChecked(True)
        self.assertFalse(dlg._ok.isEnabled())
        dlg._files.add_paths(["C:/lists/a.m3u"])
        self.assertTrue(dlg._ok.isEnabled())

    def test_dropped_files_join_the_ticks_they_find(self):
        dlg = self.dialog(n_decks=1)
        dlg._files.add_paths(["C:/lists/a.m3u"])
        self.assertTrue(dlg._cb_dropped.isChecked())
        self.assertEqual(dlg.dropped_paths(), [Path("C:/lists/a.m3u")])
        self.assertEqual(self.picked(dlg), ["decks"])

    def test_files_of_an_unticked_box_stay_home(self):
        dlg = self.dialog(n_decks=1)
        dlg._files.add_paths(["C:/lists/a.m3u"])
        dlg._cb_dropped.setChecked(False)
        self.assertEqual(dlg.dropped_paths(), [])


class ExportTest(unittest.TestCase):
    """The bundle holds exactly what was ticked."""

    def host(self):
        deck = mock.Mock(_m3u_path=None)
        deck.rowCount.return_value = 1
        day = mock.Mock(_m3u_path=None)
        day.rowCount.return_value = 1
        wish = mock.Mock(_m3u_path=None)
        wish.wishlist_entries.return_value = [SONG]
        wish.deck.name = "Wishes"
        party = mock.Mock(_m3u_path=Path("D:/Gala/Party night.m3u"))
        party._row_meta.entries.return_value = [SONG]
        party.deck.name = "Party · night"
        host = mock.Mock()
        host._deckset.decks = [deck]
        host._deckset.day_decks = [day]
        host._deckset.wishlists = [wish]
        host._deckset.warmup_table = party
        host._warmup_has_content.return_value = True
        host._pick_bundle_dir.return_value = (Path("E:/Gala"), True)
        host.deck.side_effect = lambda t: t.deck
        host._bundle_jobs_for_decks.side_effect = lambda ds: (
            [(f"deck{i}", None) for i, _d in enumerate(ds)], [])
        return host

    def run_export(self, host, decks=False, day=False, party=False, wish=False, dropped=()):
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.venue_pack.return_value = False
        ask.include_decks.return_value = decks
        ask.include_day.return_value = day
        ask.include_party.return_value = party
        ask.include_wishlists.return_value = wish
        ask.dropped_paths.return_value = list(dropped)
        ask.deck_picks.return_value = []
        ask.wish_picks.return_value = []
        with mock.patch.object(main_export, "UsbExportDialog", return_value=ask) as cls:
            main_export.ExportMixin._export_bundle(host)
        return cls

    @staticmethod
    def titles(host):
        return [title for title, _fn in host._write_bundle.call_args.args[1]]

    def test_the_dialog_is_told_how_many_party_titles_there_are(self):
        host = self.host()
        cls = self.run_export(host, decks=True)
        self.assertEqual(cls.call_args.kwargs["n_party"], 1)

    def test_a_party_list_the_panel_does_not_show_counts_nothing(self):
        host = self.host()
        host._warmup_has_content.return_value = False
        cls = self.run_export(host, decks=True)
        self.assertEqual(cls.call_args.kwargs["n_party"], 0)

    def test_every_source_together(self):
        host = self.host()
        self.run_export(host, decks=True, day=True, party=True, wish=True,
                        dropped=[Path("C:/lists/Saved.m3u")])
        self.assertEqual(self.titles(host),
                         ["deck0", "deck1", "Party - night", "Wishes", "Saved"])

    def test_party_and_wishlist_without_a_deck(self):
        host = self.host()
        self.run_export(host, party=True, wish=True)
        self.assertEqual(self.titles(host), ["Party - night", "Wishes"])

    def test_the_decks_alone_leave_the_party_list_home(self):
        host = self.host()
        self.run_export(host, decks=True)
        self.assertEqual(self.titles(host), ["deck0"])

    def test_the_party_list_writes_its_titles(self):
        host = self.host()
        self.run_export(host, party=True)
        _title, write = host._write_bundle.call_args.args[1][0]
        out = Path(tempfile.mkdtemp(prefix="dp_usb_party_")) / "Party.m3u"
        self.assertIn("a.mp3", Path(write(out)).read_text(encoding="utf-8"))

    def test_a_dragged_in_file_is_copied_as_it_is(self):
        folder = Path(tempfile.mkdtemp(prefix="dp_usb_saved_"))
        saved = folder / "Saved.m3u"
        saved.write_text("#EXTM3U\n", encoding="utf-8")
        host = self.host()
        self.run_export(host, wish=True, dropped=[saved])
        _title, write = host._write_bundle.call_args.args[1][-1]
        out = folder / "copy.m3u"
        self.assertEqual(write(out), out)
        self.assertEqual(out.read_text(encoding="utf-8"), "#EXTM3U\n")

    def test_the_bundle_name_looks_at_the_party_list_too(self):
        host = self.host()
        with mock.patch.object(main_export, "bundle_name_guess",
                               return_value="Gala") as guess:
            self.run_export(host, party=True, dropped=[Path("C:/lists/Saved.m3u")])
        self.assertEqual(guess.call_args.args[0],
                         [Path("D:/Gala/Party night.m3u"), Path("C:/lists/Saved.m3u")])

    def test_nothing_to_write_says_so(self):
        host = self.host()
        self.run_export(host)
        host._write_bundle.assert_not_called()
        host._pick_bundle_dir.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
