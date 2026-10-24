#!/usr/bin/env python3
"""🌅 Fading a title in from silence (⚙ Settings ▸ Sound & player).

Run:  py -m unittest tests.player.test_fade_in -v

Off by default. When it is on, the big player starts every title at silence
and brings it up over the set seconds of music heard — so a pause holds the
ramp, and a skipped silent intro starts it over where the music begins. A
title a 🔀 crossfade brings in already has its own ramp, and the floating
overlay is a pre-listen that starts at full level.
"""

import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fade_in_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QWidget

from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.mix import OutputMix, fade_in_secs
from player.audio.playback_state import PlaybackState
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget

TRACK = Path(r"C:\music\WW.mp3")


class _Media:
    def __init__(self, pos_ms=0):
        self.pos = pos_ms
        self.seeks = []

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return self.pos

    def playbackRate(self):
        return 1.0

    def setPosition(self, ms):
        self.seeks.append(ms)
        self.pos = ms


class _Bar:
    def showMessage(self, *_a):
        pass


class _Desk(PlayerControlMixin, QWidget):
    """The fade-in on its own: no backend, no countdown, no timed end."""

    def __init__(self, secs=4.0, playing_mode=True):
        QWidget.__init__(self)
        self._settings = {"fade_in_secs": secs}
        self.media = _Media()
        self._player = cast(Any, self.media)
        self._playback = PlaybackState()
        self._playback.path = TRACK
        self._mix = OutputMix()
        self._between = BetweenDances()
        self._between.pending = None
        self._fade_now = FadeNow()
        self._silences = {}
        self._playing_mode = playing_mode
        self.volumes = []

    def _is_playing_mode(self):
        return self._playing_mode

    def _apply_volume(self):
        self.volumes.append(self._mix.fade_in)

    def statusBar(self) -> Any:
        return _Bar()

    def _sync_big_player_limit(self):
        pass

    def _track_duration(self, path: Path) -> float:
        return 180.0


class FadeInSettingTest(unittest.TestCase):

    def test_off_unless_set(self):
        self.assertEqual(fade_in_secs({}), 0.0)

    def test_reads_the_seconds(self):
        self.assertEqual(fade_in_secs({"fade_in_secs": 2.5}), 2.5)

    def test_a_broken_value_is_off_rather_than_an_error(self):
        self.assertEqual(fade_in_secs({"fade_in_secs": "soon"}), 0.0)
        self.assertEqual(fade_in_secs({"fade_in_secs": -3}), 0.0)

    def test_bounded(self):
        self.assertEqual(fade_in_secs({"fade_in_secs": 600}), 10.0)


class FadeInTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _desk(self, **kw):
        desk = _Desk(**kw)
        self.addCleanup(reap_widget, desk)
        return desk

    def test_a_load_starts_the_title_at_silence(self):
        desk = self._desk()
        desk._arm_fade_in(TRACK)
        self.assertEqual(desk._mix.fade_in, 0.0)
        self.assertEqual(desk._playback.fade_in_from, 0.0)
        # …and the waveform is told how long it runs.
        self.assertEqual(desk._playback.fade_in_secs, 4.0)

    def test_off_by_default_nothing_changes(self):
        desk = self._desk(secs=0)
        desk._arm_fade_in(TRACK)
        self.assertEqual(desk._mix.fade_in, 1.0)
        self.assertIsNone(desk._playback.fade_in_from)
        self.assertEqual(desk._playback.fade_in_secs, 0.0)

    def test_a_crossfade_brings_its_title_in_on_its_own_ramp(self):
        desk = self._desk()
        desk._between.xfade.state = "fading"
        desk._between.xfade.incoming = TRACK
        desk._mix.fade_in = 0.3
        desk._playback.fade_in_secs = 4.0    # the title before had one
        desk._arm_fade_in(TRACK)
        self.assertEqual(desk._mix.fade_in, 0.3)
        self.assertIsNone(desk._playback.fade_in_from)
        self.assertEqual(desk._playback.fade_in_secs, 0.0)

    def test_the_overlay_pre_listen_starts_at_full_level(self):
        desk = self._desk(playing_mode=False)
        desk._arm_fade_in(TRACK)
        self.assertEqual(desk._mix.fade_in, 1.0)
        self.assertIsNone(desk._playback.fade_in_from)

    def test_the_ramp_follows_the_music_heard(self):
        desk = self._desk()
        desk._arm_fade_in(TRACK)
        desk.media.pos = 1000
        desk._step_fade_in()
        self.assertAlmostEqual(desk._mix.fade_in, 0.25)
        desk.media.pos = 4000
        desk._step_fade_in()
        self.assertEqual(desk._mix.fade_in, 1.0)
        self.assertIsNone(desk._playback.fade_in_from)   # done: no more steps
        self.assertEqual(desk.volumes, [0.25, 1.0])

    def test_a_crossfade_owns_the_level_while_it_runs(self):
        desk = self._desk()
        desk._arm_fade_in(TRACK)
        desk._between.xfade.state = "fading"
        desk._mix.fade_in = 0.6
        desk.media.pos = 1000
        desk._step_fade_in()
        self.assertEqual(desk._mix.fade_in, 0.6)

    def test_a_skipped_silent_intro_starts_the_ramp_where_the_music_does(self):
        desk = self._desk()
        desk._silences = {str(TRACK): [(0.0, 6.0)]}
        desk._arm_fade_in(TRACK)
        desk.media.pos = 400
        desk._step_fade_in()
        self.assertTrue(desk._maybe_skip_silence())
        desk._step_fade_in()
        self.assertEqual(desk._mix.fade_in, 0.0)
        desk.media.pos += 2000
        desk._step_fade_in()
        self.assertAlmostEqual(desk._mix.fade_in, 0.5)

    def test_the_play_tick_steps_it(self):
        desk = self._desk(playing_mode=False)   # …and stops before the cut
        desk._playback.fade_in_from = 0.0
        desk._mix.fade_in = 0.0
        desk.media.pos = 2000
        desk._on_play_tick()
        self.assertAlmostEqual(desk._mix.fade_in, 0.5)


class FadeInSettingDialogTest(unittest.TestCase):
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
        self.assertEqual(dlg._fade_in_spin.value(), 0.0)
        self.assertEqual(dlg.values()["fade_in_secs"], 0.0)

    def test_the_pick_is_saved(self):
        dlg = self._dialog({"fade_in_secs": 2.0})
        self.assertEqual(dlg._fade_in_spin.value(), 2.0)
        dlg._fade_in_spin.setValue(3.5)
        self.assertEqual(dlg.values()["fade_in_secs"], 3.5)

    def test_its_text_is_translated(self):
        # Widget text reaches the catalog through the text hook, not a t()
        # call, so test_i18n_catalog_keys never sees it.
        from planner.i18n.lang_de import CATALOG
        dlg = self._dialog({})
        for text in (dlg._fade_in_spin.toolTip(),
                     dlg._fade_in_spin.specialValueText(),
                     "🌅  Fade each title in over:"):
            with self.subTest(text=text[:20]):
                self.assertIn(text, CATALOG)


if __name__ == "__main__":
    unittest.main(verbosity=2)
