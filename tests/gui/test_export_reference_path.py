#!/usr/bin/env python3
"""A saved .m3u names every track under the Referenzpfad.

Run:  py -m unittest tests.gui.test_export_reference_path -v

The same library sits on C: and on F:, and a playlist built on the desk can
hold titles from both. Whatever the Referenzpfad (Settings) names is the copy
the written file points at — a track with no copy there keeps its own path.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_export_ref_"))

from dancesport_planner import MusicEntry, MusicLibrary  # noqa: E402
from tests.qt_test_support import (  # noqa: E402
    reap_widget, stub_window_startup)

_TMP = Path(tempfile.mkdtemp(prefix="dp_export_ref_files_"))
_C = _TMP / "C" / "my music" / "tanzcds"      # the Referenzpfad
_F = _TMP / "F" / "my music" / "tanzcds"      # the second copy


def _file(root: Path, rel: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch()
    return p


def _entry(path: Path, dance="CC"):
    return MusicEntry(path=path, title=path.stem, dance=dance, duration=180)


def _track_lines(m3u: Path) -> list[str]:
    return [ln for ln in m3u.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")]


class ExportReferencePathTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_export_ref_qs_"))
        cls.app = QApplication.instance() or QApplication([])

        cls.gui = stub_window_startup(cls)

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._settings["reference_path"] = str(_C)
        # A C: title, the F: copy of a title that also sits on C:, and an F:
        # title that has no C: copy at all.
        self.on_c = _file(_C, r"lateincd\c1.mp3")
        _file(_C, r"lateincd\both.mp3")
        self.on_f = _file(_F, r"lateincd\both.mp3")
        self.only_f = _file(_F, r"lateincd\only_f.mp3")
        tracks = [_entry(self.on_c), _entry(self.on_f), _entry(self.only_f)]
        self.win._lib = MusicLibrary()
        self.win._lib.entries = tracks
        self.table = self.win._tableB
        self.table.load_player_list(tracks, "Party", play_cb=None)

    def save_as(self, name: str) -> Path:
        """Save the deck as `name`; the ⚠ warning it raised (a mock) is in
        `self.warning`."""
        from gui import main_export
        out = _TMP / name
        with mock.patch.object(main_export.QFileDialog, "getSaveFileName",
                               return_value=(str(out), "")), \
                mock.patch.object(main_export, "save_settings"), \
                mock.patch.object(main_export.QMessageBox, "warning") as warning:
            self.win._on_table_save_requested(self.table)
        self.warning = warning
        return out

    def save_all(self) -> tuple[Path, str]:
        """Save all decks; (the one written file, the summary box's text)."""
        from gui import main_export
        out_dir = _TMP / "all"
        for old in out_dir.glob("*.m3u"):
            old.unlink()
        box = mock.MagicMock()
        box.clickedButton.return_value = None
        with mock.patch.object(main_export, "OUTPUT_DIR", out_dir), \
                mock.patch("planner.m3u.OUTPUT_DIR", out_dir), \
                mock.patch.object(main_export, "QMessageBox", return_value=box):
            self.win._save_all_playlists()
        written = list(out_dir.glob("*.m3u"))
        self.assertEqual(len(written), 1, written)
        return written[0], box.setText.call_args.args[0]

    def test_save_as_moves_the_second_copy_onto_the_referenzpfad(self):
        lines = _track_lines(self.save_as("party.m3u"))
        self.assertEqual(lines, [str(self.on_c), str(_C / "lateincd" / "both.mp3"),
                                 str(self.only_f)])

    def test_no_referenzpfad_writes_the_paths_as_they_are(self):
        self.win._settings["reference_path"] = ""
        lines = _track_lines(self.save_as("plain.m3u"))
        self.assertEqual(lines, [str(self.on_c), str(self.on_f), str(self.only_f)])

    def test_save_all_moves_them_too(self):
        written, _text = self.save_all()
        self.assertIn(str(_C / "lateincd" / "both.mp3"), _track_lines(written))
        self.assertNotIn(str(self.on_f), _track_lines(written))

    # ── ⚠ a title with no copy under the Referenzpfad ─────────────────────────
    def test_save_as_warns_about_the_title_missing_on_the_referenzpfad(self):
        self.save_as("warn.m3u")
        self.warning.assert_called_once()
        text = self.warning.call_args.args[2]
        self.assertIn(str(self.only_f), text)
        self.assertNotIn("both.mp3", text)
        self.assertNotIn("c1.mp3", text)

    def test_save_as_stays_quiet_when_every_title_is_on_the_referenzpfad(self):
        tracks = [_entry(self.on_c), _entry(self.on_f)]
        self.table.load_player_list(tracks, "Party", play_cb=None)
        self.save_as("quiet.m3u")
        self.warning.assert_not_called()

    def test_no_referenzpfad_no_warning(self):
        self.win._settings["reference_path"] = ""
        self.save_as("noref.m3u")
        self.warning.assert_not_called()

    def test_save_all_lists_the_missing_title_in_its_summary(self):
        _written, text = self.save_all()
        self.assertIn(str(self.only_f), text)
        self.assertNotIn("both.mp3", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
