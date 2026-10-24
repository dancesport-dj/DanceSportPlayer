#!/usr/bin/env python3
"""⏩ Starting every title a few seconds in (⚙ Settings ▸ Sound & player).

Run:  py -m unittest tests.player.test_pre_roll -v

Off by default. When it is on, the big player seeks each title that far in the
moment its media is open — the same place the ↩ pick-up seeks — and, like that
pick-up and the 🔇 silence skip, the ⏳ play length ignores what was skipped.
A ↩ mark wins over it, a title a 🔀 crossfade brings in is already running,
and the floating overlay is a pre-listen that starts at the top.
"""

import unittest

from PySide6.QtWidgets import QApplication

from shared.audio.playback import pre_roll_secs
from tests.player.test_resume_mark import TRACK, _FakeWindow, _player_mixin
from tests.qt_test_support import reap_widget


class PreRollSettingTest(unittest.TestCase):

    def test_off_unless_set(self):
        self.assertEqual(pre_roll_secs({}), 0)

    def test_reads_the_seconds(self):
        self.assertEqual(pre_roll_secs({"pre_roll_secs": 4}), 4)

    def test_a_broken_value_is_off_rather_than_an_error(self):
        self.assertEqual(pre_roll_secs({"pre_roll_secs": "a bit"}), 0)
        self.assertEqual(pre_roll_secs({"pre_roll_secs": -2}), 0)

    def test_bounded(self):
        self.assertEqual(pre_roll_secs({"pre_roll_secs": 600}), 30)


class PreRollTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class Win(_FakeWindow, _player_mixin()):
            pass
        cls.Win = Win

    def _win(self, secs=5, **kw):
        w = self.Win(pos_ms=0, **kw)
        w._settings["pre_roll_secs"] = secs
        return w

    def test_the_title_starts_that_far_in(self):
        self.assertEqual(self._win()._pre_roll_ms_for(TRACK), 5000)

    def test_off_it_starts_at_the_top(self):
        self.assertEqual(self._win(secs=0)._pre_roll_ms_for(TRACK), 0)

    def test_a_resume_mark_wins(self):
        w = self._win()
        w._resume_seek_ms = 63_000
        self.assertEqual(w._pre_roll_ms_for(TRACK), 0)

    def test_a_crossfade_title_is_already_running(self):
        w = self._win()
        w._between.xfade.state = "fading"
        w._between.xfade.incoming = TRACK
        self.assertEqual(w._pre_roll_ms_for(TRACK), 0)

    def test_the_overlay_pre_listen_starts_at_the_top(self):
        self.assertEqual(self._win(big=False)._pre_roll_ms_for(TRACK), 0)

    def test_the_seek_waits_for_the_media_to_open(self):
        from PySide6.QtMultimedia import QMediaPlayer
        w = self._win()
        w._playback.pre_roll_ms = 5000
        w._on_media_status(QMediaPlayer.MediaStatus.LoadingMedia)
        self.assertEqual(w._player.seeks, [])
        self.assertEqual(w._playback.pre_roll_ms, 5000)

    def test_open_media_seeks_once_and_the_length_ignores_it(self):
        from PySide6.QtMultimedia import QMediaPlayer
        synced = []

        class Win(self.Win):
            def _sync_big_player_limit(self):
                synced.append(self._playback.offset_ms)
        w = Win(pos_ms=0)
        w._playback.pre_roll_ms = 5000
        w._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        w._on_media_status(QMediaPlayer.MediaStatus.BufferedMedia)
        self.assertEqual(w._player.seeks, [5000])
        self.assertEqual(w._playback.offset_ms, 5000)
        self.assertEqual(w._playback.pre_roll_ms, 0)
        self.assertEqual(synced, [5000])   # the ⏳ marker moves on with it


class PreRollSettingDialogTest(unittest.TestCase):
    """The seconds sit in ⚙ Settings ▸ Sound & player, not on the panel."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dialog(self, settings):
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog(settings)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_off_by_default(self):
        dlg = self._dialog({})
        self.assertEqual(dlg._pre_roll_spin.value(), 0)
        self.assertEqual(dlg.values()["pre_roll_secs"], 0)

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"pre_roll_secs": 3})
        self.assertEqual(dlg._pre_roll_spin.value(), 3)
        dlg._pre_roll_spin.setValue(8)
        self.assertEqual(dlg.values()["pre_roll_secs"], 8)

    def test_its_text_is_translated(self):
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._pre_roll_spin.toolTip(),
                     dlg._pre_roll_spin.specialValueText(),
                     "⏩  Start each title this far in:"):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
