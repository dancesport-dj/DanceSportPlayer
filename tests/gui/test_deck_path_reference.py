#!/usr/bin/env python3
"""🧭 Fix paths, tab "Open playlists": a valid track that is not on the
Referenzpfad is reported, not passed as "all valid".

Run:  py -m unittest tests.gui.test_deck_path_reference -v

The library exists twice (C: and F:). A deck mixing both plays fine, so the
tab only repairs broken references and said ✅ for every track. It now warns
about the tracks off the Referenzpfad — the ones with a copy there and, by
title, the ones without. Opening the tab leaves them alone; 🧭 Fix swaps the
ones with a copy onto it.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_deck_path_ref_"))

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_TMP = Path(tempfile.mkdtemp(prefix="dp_deck_path_ref_files_"))
_C = _TMP / "C" / "my music" / "tanzcds"      # the Referenzpfad
_F = _TMP / "F" / "my music" / "tanzcds"      # the second copy


def _file(root: Path, rel: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _entry(path: Path, dance="CC"):
    return MusicEntry(path=path, title=path.stem, dance=dance, duration=180)


class DeckPathReferenceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_deck_path_ref_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._settings["reference_path"] = str(_C)
        self.on_c = _file(_C, r"lateincd\c1.mp3")
        _file(_C, r"lateincd\both.mp3")
        self.on_f = _file(_F, r"lateincd\both.mp3")
        self.only_f = _file(_F, r"lateincd\Only On F.mp3")
        self.win._lib = MusicLibrary()
        self.win._lib.entries = [_entry(self.on_c)]
        self.table = self.win._tableA

    def load(self, *paths: Path):
        self.table.load_player_list([_entry(p) for p in paths], "Party", play_cb=None)

    def deck_paths(self) -> list[Path]:
        return [Path(m.entry.path) for _r, m in self.table._row_meta.numbered()]

    def test_tracks_off_the_referenzpfad_are_warned_about(self):
        self.load(self.on_c, self.on_f, self.only_f)
        text = self.win._run_deck_path_fix()
        self.assertNotIn("All track paths are valid", text)
        self.assertIn("2 valid tracks are not on the Referenzpfad", text)
        self.assertIn("1 has a copy there", text)
        self.assertIn("Only On F", text)
        self.assertNotIn("both", text.split("Referenzpfad", 1)[1].split("no copy", 1)[1])

    def test_the_deck_keeps_its_valid_paths(self):
        self.load(self.on_c, self.on_f, self.only_f)
        self.win._run_deck_path_fix()
        self.assertEqual(self.deck_paths(), [self.on_c, self.on_f, self.only_f])

    def test_a_deck_all_on_the_referenzpfad_is_all_valid(self):
        self.load(self.on_c)
        text = self.win._run_deck_path_fix()
        self.assertIn("All track paths are valid", text)
        self.assertNotIn("not on the Referenzpfad", text)

    def test_no_referenzpfad_no_warning(self):
        self.win._settings["reference_path"] = ""
        self.load(self.on_c, self.on_f, self.only_f)
        text = self.win._run_deck_path_fix()
        self.assertIn("All track paths are valid", text)
        self.assertNotIn("not on the Referenzpfad", text)

    # ── 🧭 Fix: swap the tracks that have a copy there ─────────────────────────
    def test_the_swap_moves_the_copies_onto_the_referenzpfad(self):
        self.load(self.on_c, self.on_f, self.only_f)
        self.assertEqual(self.win._swap_decks_to_reference(), 1)
        self.assertEqual(self.deck_paths(),
                         [self.on_c, _C / "lateincd" / "both.mp3", self.only_f])
        swapped = self.table._row_meta.numbered()[1][1].entry
        self.assertEqual((swapped.title, swapped.dance), ("both", "CC"))

    def test_after_the_swap_only_the_title_without_a_copy_is_named(self):
        self.load(self.on_c, self.on_f, self.only_f)
        self.win._swap_decks_to_reference()
        text = self.win._run_deck_path_fix()
        self.assertIn("1 valid track is not on the Referenzpfad", text)
        self.assertNotIn("a copy there", text)
        self.assertIn("Only On F", text)

    def test_the_fix_button_swaps_on_the_open_playlists_tab(self):
        from PySide6.QtWidgets import QPushButton

        from gui import main_paths
        self.load(self.on_c, self.on_f, self.only_f)
        seen = {}

        def _exec(dlg):
            btn = next(b for b in dlg.findChildren(QPushButton) if "Fix" in b.text())
            seen["enabled_before"] = btn.isEnabled()
            btn.click()
            seen["enabled_after"] = btn.isEnabled()
            return 0

        with mock.patch.object(main_paths.QDialog, "exec", _exec):
            self.win._fix_deck_paths()
        self.assertTrue(seen["enabled_before"])
        self.assertEqual(self.deck_paths(),
                         [self.on_c, _C / "lateincd" / "both.mp3", self.only_f])
        self.assertFalse(seen["enabled_after"])

    # ── the wishlists are playlists too ────────────────────────────────────────
    def load_wish(self, *paths: Path):
        self.wish = self.win._wishlists[0]
        self.wish.load_wishlist([_entry(p) for p in paths], play_cb=None, suggester=None)

    def wish_paths(self) -> list[Path]:
        return [Path(e.path) for e in self.wish.wishlist_entries()]

    def test_a_wishlist_track_off_the_referenzpfad_is_warned_about(self):
        self.load_wish(self.on_c, self.on_f, self.only_f)
        text = self.win._run_deck_path_fix()
        self.assertIn("2 valid tracks are not on the Referenzpfad", text)
        self.assertIn("Only On F", text)

    def test_the_swap_moves_wishlist_tracks_too(self):
        self.load_wish(self.on_c, self.on_f, self.only_f)
        self.assertEqual(self.win._swap_decks_to_reference(), 1)
        self.assertEqual(self.wish_paths(),
                         [self.on_c, _C / "lateincd" / "both.mp3", self.only_f])

    def test_a_broken_wishlist_track_is_relocated(self):
        gone = _TMP / "gone" / "my music" / "tanzcds" / "lateincd" / "c1.mp3"
        self.load_wish(gone)
        self.win._run_deck_path_fix()
        self.assertEqual(self.wish_paths(), [self.on_c])

    def test_the_fix_button_stays_off_with_nothing_to_swap(self):
        from PySide6.QtWidgets import QPushButton

        from gui import main_paths
        self.load(self.on_c, self.only_f)
        seen = {}

        def _exec(dlg):
            btn = next(b for b in dlg.findChildren(QPushButton) if "Fix" in b.text())
            seen["enabled"] = btn.isEnabled()
            return 0

        with mock.patch.object(main_paths.QDialog, "exec", _exec):
            self.win._fix_deck_paths()
        self.assertFalse(seen["enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
