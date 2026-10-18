#!/usr/bin/env python3
"""⚙ Settings → 🔊 Sound & player: an output per source.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_audio_outputs_setting -v

Four pickers — music, filler, cartwall, announcements — each offering every
output the operating system lists. A saved card that is not plugged in stays
chosen (marked ⚠) instead of silently turning into "default".
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_outputs_setting_"))

from PySide6.QtWidgets import QApplication, QDialog, QTabWidget

import dancesport_gui as gui
from gui.window import main_global
from gui.dialogs import settings_dialog
from shared.audio.playback import OUTPUT_SOURCES, SYSTEM_DEFAULT
from tests.qt_test_support import reap_widget

_OUTPUTS = [("aa", "Out 1/2 (USB interface)"), ("bb", "Out 3/4 (USB interface)")]


class PickerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        with mock.patch.object(settings_dialog, "audio_output_choices",
                               return_value=list(_OUTPUTS)):
            dlg = settings_dialog.SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def _pick(self, dlg, source, data):
        combo = dlg._output_combos[source]
        combo.setCurrentIndex(combo.findData(data))

    def test_one_picker_per_source_on_the_sound_tab(self):
        dlg = self._dialog({})
        # …and 🎧 pre-listen, which is no source of the evening.
        self.assertEqual(set(dlg._output_combos), set(OUTPUT_SOURCES) | {"cue"})
        tabs = dlg.findChild(QTabWidget)
        captions = [tabs.tabText(i) for i in range(tabs.count())]
        page = tabs.widget(captions.index("🔊 Sound && player"))
        for combo in dlg._output_combos.values():
            self.assertTrue(page.isAncestorOf(combo))

    def test_pre_listen_comes_right_below_the_music(self):
        """Music and 🎧 first; filler and announcements, which rarely need an
        output of their own, last, below a line."""
        self.assertEqual(list(self._dialog({})._output_combos),
                         ["music", "cue", "cartwall", "filler", "announcer"])

    def test_pre_listen_starts_on_same_as_the_music(self):
        combo = self._dialog({})._output_combos["cue"]
        self.assertEqual(combo.currentText(), "Same as the music")
        self.assertIsNone(combo.currentData())

    def test_nothing_chosen_saves_nothing(self):
        self.assertEqual(self._dialog({}).values()["audio_outputs"], {})

    def test_every_output_is_offered(self):
        combo = self._dialog({})._output_combos["cartwall"]
        texts = [combo.itemText(i) for i in range(combo.count())]
        self.assertIn("Out 3/4 (USB interface)", texts)

    def test_a_choice_is_saved_with_its_name(self):
        dlg = self._dialog({})
        self._pick(dlg, "music", "aa")
        self._pick(dlg, "cartwall", "bb")
        self._pick(dlg, "announcer", SYSTEM_DEFAULT)
        self.assertEqual(dlg.values()["audio_outputs"], {
            "music": {"id": "aa", "name": "Out 1/2 (USB interface)"},
            "cartwall": {"id": "bb", "name": "Out 3/4 (USB interface)"},
            "announcer": {"id": SYSTEM_DEFAULT}})

    def test_the_music_has_no_follow_the_music_entry(self):
        combo = self._dialog({})._output_combos["music"]
        self.assertEqual(combo.findData(SYSTEM_DEFAULT), -1)
        self.assertEqual(combo.currentIndex(), 0)

    def test_a_saved_choice_is_shown(self):
        dlg = self._dialog({"audio_outputs": {"filler": {"id": "bb", "name": "x"}}})
        self.assertEqual(dlg._output_combos["filler"].currentData(), "bb")

    def test_a_card_not_plugged_in_stays_chosen(self):
        saved = {"music": {"id": "cc", "name": "Out 5/6 (USB interface)"}}
        dlg = self._dialog({"audio_outputs": saved})
        combo = dlg._output_combos["music"]
        self.assertEqual(combo.currentData(), "cc")
        self.assertIn("⚠", combo.currentText())
        self.assertIn("Out 5/6 (USB interface)", combo.currentText())
        self.assertEqual(dlg.values()["audio_outputs"], saved)

    def test_a_card_windows_numbered_anew_is_found_by_its_name(self):
        """🔊 "(2- ESI …)" saved, "(3- ESI …)" plugged in under a new id: it
        is that card, shown without a ⚠ and saved under its new id."""
        saved = {"music": {"id": "old", "name": "MAYA44USB Ch12 (2- ESI Audio Device)"}}
        outputs = [*_OUTPUTS, ("new", "MAYA44USB Ch12 (3- ESI Audio Device)")]
        with mock.patch.object(settings_dialog, "audio_output_choices",
                               return_value=outputs):
            dlg = settings_dialog.SettingsDialog({"audio_outputs": saved})
        self.addCleanup(reap_widget, dlg)
        combo = dlg._output_combos["music"]
        self.assertEqual(combo.currentData(), "new")
        self.assertNotIn("⚠", "".join(combo.itemText(i) for i in range(combo.count())))
        self.assertEqual(dlg.values()["audio_outputs"]["music"],
                         {"id": "new", "name": "MAYA44USB Ch12 (3- ESI Audio Device)"})


class _Dialog:

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**self._given, "audio_outputs": {"music": {"id": "aa", "name": "x"}}}

    def running_look_touched(self):
        return False


class SaveAppliesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_saving_moves_the_outputs_at_once(self):
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: {"app_mode": "both"})
        patch.start()
        self.addCleanup(patch.stop)
        win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            p = mock.patch.object(main_global, name, value)
            p.start()
            self.addCleanup(p.stop)
        with mock.patch.object(win._audio_device, "sync") as sync:
            win._open_settings()
        sync.assert_called()

    def test_the_wall_is_put_on_its_output_when_it_is_built(self):
        patch = mock.patch.object(gui, "load_settings",
                                  lambda *a, **kw: {"app_mode": "both"})
        patch.start()
        self.addCleanup(patch.stop)
        win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        if win._cart_voices is None:
            self.skipTest("no Qt Multimedia")
        self.assertIn("cartwall", win._audio_device._applied)


if __name__ == "__main__":
    unittest.main()
