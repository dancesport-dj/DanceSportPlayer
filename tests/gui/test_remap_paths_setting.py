#!/usr/bin/env python3
"""The 'Search folders' setting: from the Settings dialog to 🧭 Fix paths.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_remap_paths_setting -v

The folders are typed on one PC and used on another, so the two ends have to
agree: what the text box saves is a list, and the path fixer must search the
Referenzpfad AND those folders — the Referenzpfad first, so a machine that was
already set up keeps deciding what it decided before.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_remapset_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.dialogs import SettingsDialog  # noqa: E402
from planner.cartwall import CartPad, Page  # noqa: E402
from gui.main_paths import PathFixMixin  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402


class SettingsRoundTripTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_the_saved_folders_come_back_into_the_box(self):
        dlg = self._dlg({"remap_paths": ["F:\\my music", "C:\\Users\\M\\my music"]})
        self.assertEqual(dlg._remap_edit.toPlainText(),
                         "F:\\my music\nC:\\Users\\M\\my music")

    def test_typed_folders_are_saved_as_a_list(self):
        dlg = self._dlg({})
        dlg._remap_edit.setPlainText("F:\\my music\n\nC:\\Users\\M\\my music\n")
        self.assertEqual(dlg.values()["remap_paths"],
                         ["F:\\my music", "C:\\Users\\M\\my music"])

    def test_an_untouched_dialog_saves_no_folders(self):
        self.assertEqual(self._dlg({}).values()["remap_paths"], [])


class _Win(PathFixMixin):
    """The path fixer reduced to what `_remap_index` reads."""

    def __init__(self, settings):
        self._settings = settings
        self._lib = None


class RemapIndexTest(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_remapidx_"))
        self.track = self.tmp / "extern" / "tanzcds" / "lateincd" / "x.mp3"
        self.track.parent.mkdir(parents=True)
        self.track.write_bytes(b"x")
        self.foreign = Path("C:/somewhere else/tanzcds/lateincd/x.mp3")

    def test_a_second_folder_finds_what_the_referenzpfad_does_not(self):
        win = _Win({"reference_path": str(self.tmp / "nothing here"),
                    "remap_paths": [str(self.tmp / "extern")]})
        _, _, remapper = win._remap_index()
        self.assertEqual(remapper.remap(self.foreign), self.track)

    def test_the_referenzpfad_stays_the_first_folder_searched(self):
        win = _Win({"reference_path": "F:\\my music",
                    "remap_paths": ["C:\\other"]})
        _, _, remapper = win._remap_index()
        self.assertEqual([str(r) for r in remapper.roots],
                         ["F:\\my music", "C:\\other"])

    def test_neither_setting_leaves_the_fixer_with_nothing_to_search(self):
        _, _, remapper = _Win({})._remap_index()
        self.assertFalse(remapper)


class _Wall:
    """CartwallWidget reduced to what the path fixer touches."""

    def __init__(self, pages):
        self._pages = pages
        self.refreshed = 0

    def pages(self):
        return self._pages

    def refresh_missing(self):
        self.refreshed += 1


class CartwallFixTest(unittest.TestCase):
    """🧭 also re-points the 🎛 pads — they are filled once and never rebuilt."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="dp_padfix_"))
        self.sample = self.tmp / "special" / "15-Tusch.mp3"
        self.sample.parent.mkdir(parents=True)
        self.sample.write_bytes(b"x")
        self.foreign = "C:/gone/special/15-Tusch.mp3"

    def _win(self, pad_path):
        win = _Win({"reference_path": str(self.tmp)})
        win._cartwall = _Wall([Page(pads={(0, 0): CartPad(path=pad_path)})])
        win.saved = 0
        win._save_cartwall = lambda: setattr(win, "saved", win.saved + 1)
        return win

    def test_a_gone_pad_is_repointed_saved_and_redrawn(self):
        win = self._win(self.foreign)
        _, _, remapper = win._remap_index()
        moved = win._fix_cartwall_paths(remapper)
        self.assertEqual(len(moved), 1)
        self.assertEqual(win._cartwall.pages()[0].pads[(0, 0)].path, str(self.sample))
        self.assertEqual((win.saved, win._cartwall.refreshed), (1, 1))

    def test_a_wall_that_needs_nothing_is_not_saved(self):
        """Saving on every 🧭 run would rewrite cartwall.json for no reason."""
        win = self._win(str(self.sample))
        _, _, remapper = win._remap_index()
        self.assertEqual(win._fix_cartwall_paths(remapper), [])
        self.assertEqual((win.saved, win._cartwall.refreshed), (0, 0))

    def test_a_window_without_a_wall_is_fine(self):
        """The planner-only mode never builds one."""
        win = _Win({"reference_path": str(self.tmp)})
        _, _, remapper = win._remap_index()
        self.assertEqual(win._fix_cartwall_paths(remapper), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
