"""🎚 The ♪ button on the big player lights up in the TSO blue while any
equalizer tab (music, voice, cue) is on, so the desk sees at a glance an EQ is in."""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_eq_lit_"))

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QApplication

from planner.playing import equalizer as eqs
from player.audio import pair_route
from player.widgets.player import BigPlayerWidget
from tests.player.test_audio_idle import _Desk
from tests.qt_test_support import reap_widget


def _eqs_on(**on: bool) -> dict:
    """{"equalizer": ...} with each named source switched as given."""
    out = {}
    for source, state in on.items():
        cfg = eqs.default_eq(source)
        cfg["on"] = state
        out[source] = cfg
    return {"equalizer": out}


def _music_on(on: bool) -> dict:
    return _eqs_on(music=on)


class _Test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])


class DeviceSaysTest(_Test):

    def setUp(self):
        # A tapped music stream starts the audio thread; left running, the
        # process aborts at exit (exit 127 after "OK").
        self.addCleanup(pair_route.stop_audio_thread)
        self.desk = _Desk()
        self.lit = []
        self.desk.device.eq_lit = self.lit.append

    # ===== Acceptance criteria =====

    def test_the_music_eq_on_lights_the_button(self):
        self.desk.settings.update(_music_on(True))
        with mock.patch("player.audio.eq.available", return_value=True):
            self.desk.device.sync_eq()
        self.assertEqual(self.lit[-1], True)

    def test_the_music_eq_off_puts_it_out(self):
        self.desk.settings.update(_music_on(False))
        self.desk.device.sync_eq()
        self.assertEqual(self.lit[-1], False)

    def test_the_voice_eq_on_lights_it_with_the_music_off(self):
        self.desk.settings.update(_eqs_on(music=False, announcer=True))
        with mock.patch("player.audio.eq.available", return_value=True):
            self.desk.device.sync_eq()
        self.assertEqual(self.lit[-1], True)

    def test_the_cue_eq_on_lights_it_with_the_music_off(self):
        self.desk.settings.update(_eqs_on(music=False, cue=True))
        with mock.patch("player.audio.eq.available", return_value=True):
            self.desk.device.sync_eq()
        self.assertEqual(self.lit[-1], True)

    def test_every_tab_off_puts_it_out(self):
        self.desk.settings.update(_eqs_on(music=False, announcer=False, cue=False))
        with mock.patch("player.audio.eq.available", return_value=True):
            self.desk.device.sync_eq()
        self.assertEqual(self.lit[-1], False)

    # ===== Coverage and null checks =====

    def test_without_a_listener_nothing_breaks(self):
        self.desk.device.eq_lit = None
        self.desk.device.sync_eq()


class ButtonTest(_Test):

    def setUp(self):
        self.card = BigPlayerWidget(QMediaPlayer(), QAudioOutput())
        self.addCleanup(reap_widget, self.card)
        self.card.resize(900, 500)
        self.card.show()

    def lit(self) -> bool:
        return bool(self.card._tools_btn.property("lit"))

    # ===== Acceptance criteria =====

    def test_the_eq_on_lights_the_button_in_the_tso_blue(self):
        self.card.set_eq_on(True)
        self.assertTrue(self.lit())
        self.assertIn("#1565c0", self.card._tools_btn.styleSheet())
        self.assertIn("#1565c0", self.card._tso_btn.styleSheet())

    # ===== Core behavior =====

    def test_closing_the_tempo_check_keeps_it_lit_while_the_eq_is_on(self):
        self.card.set_eq_on(True)
        self.card._takt_act.setChecked(True)
        self.card._takt_act.setChecked(False)
        self.assertTrue(self.lit())

    def test_the_eq_off_puts_it_out(self):
        self.card.set_eq_on(True)
        self.card.set_eq_on(False)
        self.assertFalse(self.lit())


if __name__ == "__main__":
    unittest.main()
