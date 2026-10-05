#!/usr/bin/env python3
"""Saving the Eintanzen panel writes a party list, not a competition draw.

Run:  py -m unittest tests.gui.test_export_party_panel -v

"Save as M3U…" on the 🤸 Eintanzen panel used to go down the GRID branch of
`_on_table_save_requested`, because the panel is neither a deck nor a wishlist.
The file it produced opened with "# ══  (1 Heat) ══" — an empty round name — and
carried one "# ── Tango ──" per single track: a competition draw's scaffolding
wrapped around a flat running order, which is not what a party list is.

A party list is flat, so it goes out flat, with its ROUNDS written in
(planner.m3u.export_flat_m3u).
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_export_party_gui_"))

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_TMP = Path(tempfile.mkdtemp(prefix="dp_export_party_gui_files_"))

# One evening: Standard, Latin, a social title, Standard, Latin.
_PARTY = (["LW", "TG", "QS"] + ["SA", "CC", "RB"] + ["DISCOFOX"]
          + ["LW", "SF", "QS"] + ["CC", "RB", "JI"])


def _entry(dance: str, i: int) -> MusicEntry:
    if dance == "DISCOFOX":
        return MusicEntry(path=_TMP / f"df{i}.mp3", title=f"Social {i}",
                          dance=None, other_genre="Discofox", duration=180)
    return MusicEntry(path=_TMP / f"{dance}{i}.mp3", title=f"{dance} {i}",
                      dance=dance, duration=180)


class PartyPanelExportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_export_party_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.entries = [_entry(d, i) for i, d in enumerate(_PARTY)]
        self.win._lib = MusicLibrary()
        self.win._lib.entries = list(self.entries)
        self.table = self.win._warmup_table
        self.table.load_warmup(self.entries, "Party", style="",
                               dance_class="S", relax=True, play_cb=None,
                               suggester=None)

    def save_as(self, name: str) -> Path:
        from gui import main_export
        out = _TMP / name
        with mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                               return_value=(str(out), "")), \
                mock.patch.object(main_export, "save_settings"), \
                mock.patch.object(main_export.QMessageBox, "warning"), \
                mock.patch.object(main_export.QMessageBox, "information"):
            self.win._on_table_save_requested(self.table)
        return out

    def save_all(self) -> tuple[list[Path], str]:
        """💾 Save all: (the written .m3u files, the summary box's text)."""
        from gui import main_export
        out_dir = _TMP / "all"
        for old in out_dir.rglob("*.m3u"):
            old.unlink()
        box = mock.MagicMock()
        box.clickedButton.return_value = None
        with mock.patch.object(main_export, "OUTPUT_DIR", out_dir), \
                mock.patch("planner.m3u.OUTPUT_DIR", out_dir), \
                mock.patch.object(main_export, "QMessageBox", return_value=box):
            self.win._save_all_playlists()
        # Nothing saved → the summary box never opens, so there is no text.
        text = box.setText.call_args.args[0] if box.setText.call_args else ""
        return sorted(out_dir.rglob("*.m3u")), text

    def _lines(self, m3u: Path) -> list[str]:
        return m3u.read_text(encoding="utf-8").splitlines()

    def _comments(self, m3u: Path) -> list[str]:
        return [ln.strip("# ─═").strip() for ln in self._lines(m3u)
                if ln.startswith("#") and not ln.upper().startswith("#EXT")]

    def _tracks(self, m3u: Path) -> list[str]:
        return [ln for ln in self._lines(m3u)
                if ln.strip() and not ln.startswith("#")]

    def test_the_panel_writes_its_rounds(self):
        out = self.save_as("party.m3u")
        self.assertEqual(self._comments(out),
                         ["Standardrunde 1", "Lateinrunde 1", "Socialrunde 1",
                          "Standardrunde 2", "Lateinrunde 2"])

    def test_no_heat_scaffolding_reaches_the_file(self):
        out = self.save_as("noheats.m3u")
        text = out.read_text(encoding="utf-8")
        self.assertNotIn("Heat", text)
        self.assertNotIn("(no song found)", text)

    def test_every_title_is_written_once_in_playing_order(self):
        out = self.save_as("order.m3u")
        self.assertEqual(self._tracks(out), [str(e.path) for e in self.entries])


class SaveAllIncludesThePanelTest(PartyPanelExportTest):
    """💾 Save all walked the decks and the wishlists only, so the one list an
    evening is actually run from was the one it left behind."""

    def test_save_all_writes_the_party_list_too(self):
        written, _text = self.save_all()
        self.assertEqual(len(written), 1, written)
        self.assertEqual(self._tracks(written[0]),
                         [str(e.path) for e in self.entries])

    def test_it_goes_out_flat_with_its_rounds(self):
        written, _text = self.save_all()
        self.assertEqual(self._comments(written[0]),
                         ["Standardrunde 1", "Lateinrunde 1", "Socialrunde 1",
                          "Standardrunde 2", "Lateinrunde 2"])

    def test_the_summary_names_the_file(self):
        written, text = self.save_all()
        self.assertIn(written[0].name, text)

    def test_an_empty_panel_is_not_saved(self):
        self.table.load_warmup([], "Party", style="", dance_class="S",
                               relax=True, play_cb=None, suggester=None)
        written, _text = self.save_all()
        self.assertEqual(written, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
