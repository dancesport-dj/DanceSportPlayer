#!/usr/bin/env python3
"""Every file picker opens where the user was last.

Run:  py -m unittest tests.gui.test_browse_dir_memory -v

The open/add pickers all started in one folder computed ONCE at import — the
first of `F:\\my music`, the configured library, the OS Music folder that
exists. On a Mac the first two never do, so every pick began again in ~/Music
no matter where the files really are. The dialogs now open in the folder the
last pick came from, and remember it across restarts (settings "open_dir" for
music, "import_dir" for 📂 Import M3U); the computed folder is only the
fallback for the very first one.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_browse_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui import common  # noqa: E402
from shared import audio_files  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_ELSEWHERE = Path(tempfile.mkdtemp(prefix="dp_browse_pick_"))
_PICKED = _ELSEWHERE / "fare thee well.mp3"


class BrowseDirMemoryTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        _PICKED.touch()

    def setUp(self):
        audio_files.set_browse_dir("", None)
        self.addCleanup(audio_files.set_browse_dir, "", None)

    def test_the_first_picker_opens_in_the_configured_folder(self):
        self.assertEqual(audio_files.music_browse_dir(), audio_files._MUSIC_BROWSE_DIR)

    def test_a_pick_is_remembered_as_its_folder(self):
        audio_files.remember_browse_dir(str(_PICKED))
        self.assertEqual(audio_files.music_browse_dir(), str(_ELSEWHERE))

    def test_a_folder_that_is_gone_is_not_offered_again(self):
        audio_files.remember_browse_dir(str(_ELSEWHERE / "nowhere" / "x.mp3"))
        self.assertEqual(audio_files.music_browse_dir(), audio_files._MUSIC_BROWSE_DIR)

    def test_the_remembered_folder_is_handed_to_the_saver(self):
        saved = []
        audio_files.set_browse_dir("", saved.append)
        audio_files.remember_browse_dir(str(_PICKED))
        self.assertEqual(saved, [str(_ELSEWHERE)])

    # ── the pickers themselves ────────────────────────────────────────────────
    def _zone(self):
        z = common._DroppedFilesList()
        self.addCleanup(reap_widget, z)
        return z

    def test_the_add_files_picker_opens_where_the_last_one_ended(self):
        z = self._zone()
        seen = []

        def fake(_parent, _title, start, _filter):
            seen.append(start)
            return [str(_PICKED)], ""

        with mock.patch.object(common.QFileDialog, "getOpenFileNames", fake):
            z._browse()
            z._browse()
        self.assertEqual(seen, [audio_files._MUSIC_BROWSE_DIR, str(_ELSEWHERE)])


class SettingsMemoryTest(unittest.TestCase):
    """What the window writes into gui_settings.json, so it survives a restart."""

    def _win(self):
        from gui.main_import import ImportMixin

        class Win(ImportMixin):
            pass
        w = Win()
        w._settings = {}
        return w

    def test_the_open_folder_is_stored(self):
        w = self._win()
        with mock.patch("gui.main_import.save_settings") as save:
            w._remember_open_dir(str(_ELSEWHERE))
        self.assertEqual(w._settings["open_dir"], str(_ELSEWHERE))
        save.assert_called_once_with(w._settings)

    def test_the_import_folder_is_its_own_memory(self):
        w = self._win()
        with mock.patch("gui.main_import.save_settings"):
            w._remember_import_dir(str(_ELSEWHERE / "party.m3u"))
        self.assertEqual(w._settings["import_dir"], str(_ELSEWHERE))
        self.assertNotIn("open_dir", w._settings)

    def test_the_same_folder_twice_is_not_written_again(self):
        w = self._win()
        w._settings["import_dir"] = str(_ELSEWHERE)
        with mock.patch("gui.main_import.save_settings") as save:
            w._remember_import_dir(str(_ELSEWHERE / "party.m3u"))
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
