#!/usr/bin/env python3
"""The playlist file format the exports write — ⚙ Settings → Paths.

Run:  py -m unittest tests.planner.test_m3u_format -v

Every export wrote UTF-8 without a BOM into a .m3u. That stays the default.
A Windows tool that guesses ANSI without a BOM gets the BOM variant, and a
player that only trusts the extension gets .m3u8. Whatever the app writes,
it reads back: the 🧳 bundle re-reads the file it just wrote, and the
popularity learning walks .m3u8 files as well as .m3u.
"""

import os
import shutil
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_m3u_format_"))

from planner import config as planner_config
from planner.music import playlist_index
from planner.playlist import m3u
from planner.models import MusicEntry
from planner.playlist.playlist_text import playlist_files

_BOM = b"\xef\xbb\xbf"


class _Base(unittest.TestCase):

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_m3u_fmt_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.addCleanup(m3u.set_m3u_format, "utf-8")
        self.track = self.dir / "Küss mich (TG 32).mp3"
        self.track.write_bytes(b"ID3")
        self.entries = [MusicEntry(path=self.track, title="Küss mich", dance="TG")]

    def export(self, fmt, **kw):
        m3u.set_m3u_format(fmt)
        return Path(m3u.export_flat_m3u(self.entries, "Liste", timestamp=False,
                                        out_dir=self.dir, **kw))


class ExportFormatTest(_Base):

    def test_the_default_is_utf8_without_a_bom_in_a_m3u(self):
        out = self.export("utf-8")
        self.assertEqual(out.suffix, ".m3u")
        raw = out.read_bytes()
        self.assertFalse(raw.startswith(_BOM))
        self.assertIn("Küss mich".encode("utf-8"), raw)

    def test_utf8_with_a_bom(self):
        out = self.export("utf-8-sig")
        self.assertEqual(out.suffix, ".m3u")
        self.assertTrue(out.read_bytes().startswith(_BOM + b"#EXTM3U"))

    def test_m3u8_names_the_encoding_in_the_extension(self):
        out = self.export("m3u8")
        self.assertEqual(out.suffix, ".m3u8")
        self.assertFalse(out.read_bytes().startswith(_BOM))

    def test_a_grid_export_follows_the_setting_too(self):
        m3u.set_m3u_format("utf-8-sig")
        playlist = {"Finale": [[self.entries[0]]]}
        out = Path(m3u.export_m3u(playlist, ["TG"], "Grid", timestamp=False,
                                  out_path=self.dir / "Grid.m3u"))
        self.assertTrue(out.read_bytes().startswith(_BOM))

    def test_an_unknown_setting_falls_back_to_the_default(self):
        m3u.set_m3u_format("utf-32")
        self.assertEqual((m3u.m3u_encoding(), m3u.m3u_suffix()), ("utf-8", ".m3u"))

    def test_the_suffix_follows_the_setting(self):
        m3u.set_m3u_format("m3u8")
        self.assertEqual(m3u.m3u_suffix(), ".m3u8")


class BundleReadsItsOwnFileTest(_Base):
    """numbered_folder_m3u re-reads the file it was handed: a BOM must not
    turn '#EXTM3U' into a track line."""

    def test_a_bom_file_numbers_its_tracks_and_keeps_its_bom(self):
        folder = self.dir / "bundle"
        folder.mkdir()
        out = self.export("utf-8-sig", out_path=folder / "Liste.m3u")
        copied, missing = m3u.numbered_folder_m3u(out)
        self.assertEqual((len(copied), missing), (1, 0))
        raw = out.read_bytes()
        self.assertTrue(raw.startswith(_BOM + b"#EXTM3U"))
        self.assertIn(b"0_0_1 - ", raw)


class LearningSeesM3u8Test(unittest.TestCase):

    def test_the_playlist_folder_walk_includes_m3u8(self):
        root = Path(tempfile.mkdtemp(prefix="dp_m3u8_learn_"))
        self.addCleanup(shutil.rmtree, root, True)
        orig = planner_config.PLAYLIST_DIR
        planner_config.set_playlist_dir(root)
        self.addCleanup(planner_config.set_playlist_dir, orig)
        (root / "a.m3u").write_text("#EXTM3U\n", encoding="utf-8")
        (root / "b.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
        (root / "c.m3u.bak").write_text("#EXTM3U\n", encoding="utf-8")
        m3us, _mp3s = playlist_index._playlist_tree()
        self.assertEqual(sorted(p.name for p, _sig in m3us), ["a.m3u", "b.m3u8"])
        self.assertEqual([p.name for p in playlist_files(root)], ["a.m3u", "b.m3u8"])


class SettingsComboTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        from tests.qt_test_support import reap_widget
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_default_is_utf8(self):
        self.assertEqual(self.dialog({}).values()["m3u_format"], "utf-8")

    def test_a_saved_choice_round_trips(self):
        dlg = self.dialog({"m3u_format": "m3u8"})
        self.assertEqual(dlg.values()["m3u_format"], "m3u8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
