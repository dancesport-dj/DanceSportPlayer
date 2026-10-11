#!/usr/bin/env python3
"""〰 The waveform strip under the player card's seek bar.

Run:  py -m unittest tests.player.test_waveform -v

The peaks are pure numpy; the strip draws them with what the desk needs to
see at a glance — what has played, the dead air the player skips, the 🐂
highlights and where the ⏳ fade starts — and a click on it seeks.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_wave_"))

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from shared.audio_probes import waveform_peaks
from tests.qt_test_support import reap_widget


def _app():
    return QApplication.instance() or QApplication([])


def _mouse(kind, x, button, buttons=True):
    held = Qt.MouseButton.LeftButton if buttons else Qt.MouseButton.NoButton
    return QMouseEvent(kind, QPointF(x, 10), QPointF(x, 10), button, held,
                       Qt.KeyboardModifier.NoModifier)


class PeaksTest(unittest.TestCase):

    def test_one_peak_per_bin_scaled_to_the_loudest(self):
        x = np.array([0.1, -0.2, 0.4, -0.8, 0.2, 0.0], dtype=np.float32)
        self.assertEqual(waveform_peaks(x, 3), [0.25, 1.0, 0.25])

    def test_fewer_samples_than_bins_gives_one_bin_each(self):
        self.assertEqual(waveform_peaks(np.array([0.5, -1.0]), 10), [0.5, 1.0])

    def test_no_samples_no_peaks(self):
        self.assertEqual(waveform_peaks(np.empty(0, dtype=np.float32), 100), [])

    def test_digital_silence_is_flat_not_a_division_by_zero(self):
        self.assertEqual(waveform_peaks(np.zeros(8), 4), [0.0] * 4)


class StripTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def strip(self):
        from player.waveform import WaveformStrip
        w = WaveformStrip()
        self.addCleanup(reap_widget, w)
        w.resize(400, 34)
        w.set_span(200_000, 240_000)
        return w

    def click(self, w, x):
        self.press(w, x)
        self.release(w, x)

    def press(self, w, x):
        w.mousePressEvent(_mouse(QMouseEvent.Type.MouseButtonPress, x,
                                 Qt.MouseButton.LeftButton))

    def drag(self, w, x):
        w.mouseMoveEvent(_mouse(QMouseEvent.Type.MouseMove, x,
                                Qt.MouseButton.NoButton))

    def release(self, w, x):
        w.mouseReleaseEvent(_mouse(QMouseEvent.Type.MouseButtonRelease, x,
                                   Qt.MouseButton.LeftButton, buttons=False))

    def test_a_click_seeks_to_that_spot_of_the_bar(self):
        w = self.strip()
        seen = []
        w.seekRequested.connect(seen.append)
        self.click(w, 100)
        self.assertEqual(seen, [50_000])

    def test_scrubbing_past_the_start_lands_on_zero_like_the_seek_bar(self):
        """Marcel: "waveform scrath to beginning is not wokring so good as
        with normal seekbar"."""
        w = self.strip()
        w.set_position(150_000)
        seen, scrubbed = [], []
        w.seekRequested.connect(seen.append)
        w.scrubbed.connect(scrubbed.append)
        self.press(w, 300)
        self.drag(w, 120)
        self.drag(w, -40)               # past the left edge
        self.assertEqual(seen, [])      # the seek waits for the release
        self.assertEqual(scrubbed, [150_000, 60_000, 0])
        self.assertEqual(w.x_for(w._pos), 0)   # the playhead follows the mouse
        w.set_position(151_000)         # playback ticks do not pull it back
        self.assertEqual(w._pos, 0)
        self.release(w, -40)
        self.assertEqual(seen, [0])
        w.set_position(1_000)
        self.assertEqual(w._pos, 1_000)

    def test_a_move_without_a_press_does_not_scrub(self):
        w = self.strip()
        scrubbed = []
        w.scrubbed.connect(scrubbed.append)
        self.drag(w, 100)
        self.assertEqual(scrubbed, [])

    def test_an_empty_bar_does_not_seek(self):
        w = self.strip()
        w.set_span(0, 0)
        seen = []
        w.seekRequested.connect(seen.append)
        self.click(w, 100)
        self.assertEqual(seen, [])

    def test_the_bar_runs_to_the_actual_end_like_the_seek_bar(self):
        w = self.strip()
        self.assertEqual(w.x_for(200_000), 400)
        self.assertEqual(w.x_for(100_000), 200)

    def test_it_paints_everything_it_is_given(self):
        w = self.strip()
        w.set_peaks([0.2, 1.0, 0.5] * 100)
        w.set_position(60_000)
        w.set_silences([(0.0, 1.5), (230.0, 240.0)])
        w.set_marks([90_000, 150_000], 150_000)
        w.set_fade_start(190_000)
        img = w.grab().toImage()
        self.assertFalse(img.isNull())
        # Played and still-to-play are told apart by colour.
        self.assertNotEqual(img.pixelColor(50, 17), img.pixelColor(350, 17))

    def test_it_paints_before_the_peaks_arrive(self):
        w = self.strip()
        self.assertFalse(w.grab().toImage().isNull())

    def test_the_final_seconds_turn_it_red(self):
        w = self.strip()
        w.set_peaks([1.0] * 300)
        w.set_position(100_000)
        blue = w.grab().toImage().pixelColor(50, 17)
        w.set_ending(True)
        red = w.grab().toImage().pixelColor(50, 17)
        self.assertGreater(red.red(), red.blue())
        self.assertGreater(blue.blue(), blue.red())
        w.set_ending(False)
        self.assertEqual(w.grab().toImage().pixelColor(50, 17), blue)

    def test_the_playhead_is_a_slim_orange_line_with_caps(self):
        w = self.strip()
        w.set_peaks([1.0] * 300)
        w.set_position(100_000)         # x = 200
        img = w.grab().toImage()
        orange = (0xff, 0x98, 0x00)

        def rgb(x, y):
            c = img.pixelColor(x, y)
            return (c.red(), c.green(), c.blue())
        self.assertEqual(rgb(200, 17), orange)
        # Slim: one pixel of orange, the dark outline right beside it.
        self.assertNotEqual(rgb(199, 17), orange)
        self.assertNotEqual(rgb(201, 17), orange)
        # Capped: the top edge is orange wider than the line itself.
        self.assertEqual(rgb(197, 1), orange)


class CardTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def setUp(self):
        from PySide6.QtMultimedia import QMediaPlayer
        from player.player import BigPlayerWidget
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)
        self.card.show()
        self.track = Path(tempfile.mkdtemp(prefix="dp_wave_card_")) / "LW1.mp3"
        self.track.write_bytes(b"not really an mp3")

    def test_the_strip_is_on_by_default_and_can_be_switched_off(self):
        self.assertTrue(self.card._wave.isVisible())
        self.card.set_waveform_enabled(False)
        self.assertFalse(self.card._wave.isVisible())

    def test_switched_off_it_decodes_nothing(self):
        self.card.set_waveform_enabled(False)
        asked = []
        self.card._wave_loader.request = lambda path: asked.append(path)
        self.card.set_waveform_track(self.track)
        self.assertEqual(asked, [])

    def test_switching_it_on_loads_the_track_already_playing(self):
        self.card.set_waveform_enabled(False)
        self.card.set_waveform_track(self.track)
        self.card._wave_loader.request = lambda path: [0.5, 1.0]
        self.card.set_waveform_enabled(True)
        self.assertEqual(self.card._wave._peaks, [0.5, 1.0])

    def test_late_peaks_land_only_on_their_own_track(self):
        self.card._wave_loader.request = lambda path: None
        self.card.set_waveform_track(self.track)
        self.card._on_wave_ready(str(self.track.with_name("other.mp3")), [1.0])
        self.assertIsNone(self.card._wave._peaks)
        self.card._on_wave_ready(str(self.track), [0.3, 1.0])
        self.assertEqual(self.card._wave._peaks, [0.3, 1.0])

    def test_the_highlights_and_the_cut_reach_the_strip(self):
        self.card._dur = 240_000
        self.card.set_limit(180_000)
        self.card.set_pd_marks([90.0, 150.0], 150.0)
        self.assertEqual(self.card._wave._span, 180_000)
        self.assertEqual(self.card._wave._marks, [90_000, 150_000])
        self.assertEqual(self.card._wave._armed, 150_000)

    def test_stopping_clears_the_strip(self):
        self.card._wave_loader.request = lambda path: [1.0]
        self.card.set_waveform_track(self.track)
        self.card.set_wave_overlay([(0.0, 2.0)], 170_000)
        self.card.set_now("")
        self.assertIsNone(self.card._wave._peaks)
        self.assertEqual(self.card._wave._silences, [])
        self.assertIsNone(self.card._wave._fade_at)

    def test_the_strip_sits_above_the_seek_bar(self):
        self.assertLess(self.card._wave.geometry().top(),
                        self.card._slider.geometry().top())
        self.card.set_wide(True)
        self.assertLess(self.card._wave.geometry().top(),
                        self.card._slider.geometry().top())

    def test_the_seek_bar_can_give_way_to_the_strip(self):
        self.card.set_seek_bar_hidden(True)
        self.assertFalse(self.card._slider.isVisible())
        self.assertTrue(self.card._wave.isVisible())
        # Without the strip the card keeps a timeline after all.
        self.card.set_waveform_enabled(False)
        self.assertTrue(self.card._slider.isVisible())
        self.card.set_waveform_enabled(True)
        self.assertFalse(self.card._slider.isVisible())
        self.card.set_seek_bar_hidden(False)
        self.assertTrue(self.card._slider.isVisible())

    def test_scrubbing_the_strip_moves_the_seek_bar_and_seeks_on_release(self):
        self.card._slider.setRange(0, 200_000)
        self.card._wave.set_span(200_000, 200_000)
        sought = []
        self.card._player.setPosition = sought.append
        self.card._wave.scrubbed.emit(30_000)
        self.assertEqual(self.card._slider.value(), 30_000)
        from player.player import _fmt_ms
        self.assertEqual(self.card._elapsed.text(), _fmt_ms(30_000))
        self.card._on_position(90_000)              # a playback tick mid-drag
        self.assertEqual(self.card._slider.value(), 30_000)
        self.card._wave.seekRequested.emit(0)
        self.assertEqual(sought, [0])
        self.card._on_position(1_000)
        self.assertEqual(self.card._slider.value(), 1_000)

    def test_the_end_warning_turns_the_strip_red_with_the_seek_bar(self):
        from PySide6.QtMultimedia import QMediaPlayer
        playing = QMediaPlayer.PlaybackState.PlayingState
        self.card._player.playbackState = lambda: playing
        self.card._update_end_flash(5_000, 180_000)
        self.assertTrue(self.card._wave._ending)
        self.card._stop_end_flash()
        self.assertFalse(self.card._wave._ending)


class LoaderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def test_peaks_come_back_through_the_signal_and_are_kept(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from player import waveform
        loader = waveform.WaveformLoader(compute=lambda path: [0.1, 1.0])
        got = []
        loop = QEventLoop()
        loader.ready.connect(lambda key, peaks: (got.append((key, peaks)), loop.quit()))
        QTimer.singleShot(5000, loop.quit)
        self.assertIsNone(loader.request(Path("C:/m/a.mp3")))
        loop.exec()
        self.assertEqual(got, [(str(Path("C:/m/a.mp3")), [0.1, 1.0])])
        self.assertEqual(loader.request(Path("C:/m/a.mp3")), [0.1, 1.0])


class _Store:
    """An AudioCache stand-in: get/put_waveform only."""

    def __init__(self, known=None):
        self.known = dict(known or {})
        self.put = []

    def get_waveform(self, path):
        return self.known.get(str(path))

    def put_waveform(self, path, peaks):
        self.put.append((str(path), peaks))


class StoredLoaderTest(unittest.TestCase):
    """Marcel: "cache it in databse, currently it feels liek a second till
    wave comes" — a title decoded in an earlier session draws at once."""

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def _decoded(self, loader, path):
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        loader.ready.connect(lambda *_a: loop.quit())
        QTimer.singleShot(5000, loop.quit)
        self.assertIsNone(loader.request(path))
        loop.exec()

    def test_a_stored_outline_comes_back_without_decoding(self):
        from player import waveform
        song = Path("C:/m/a.mp3")
        store = _Store({str(song): [0.2, 1.0]})
        decoded = []
        loader = waveform.WaveformLoader(
            compute=lambda p: decoded.append(p) or [0.9], cache_of=lambda: store)
        self.assertEqual(loader.request(song), [0.2, 1.0])
        self.assertEqual(decoded, [])

    def test_a_fresh_decode_is_stored(self):
        from player import waveform
        store = _Store()
        loader = waveform.WaveformLoader(compute=lambda p: [0.1, 1.0],
                                         cache_of=lambda: store)
        self._decoded(loader, Path("C:/m/b.mp3"))
        self.assertEqual(store.put, [(str(Path("C:/m/b.mp3")), [0.1, 1.0])])

    def test_a_failed_decode_is_not_stored(self):
        # No ffmpeg today is no reason never to try again.
        from player import waveform
        store = _Store()
        loader = waveform.WaveformLoader(compute=lambda p: [], cache_of=lambda: store)
        self._decoded(loader, Path("C:/m/c.mp3"))
        self.assertEqual(store.put, [])

    def test_no_library_loaded_yet_still_decodes(self):
        from player import waveform
        loader = waveform.WaveformLoader(compute=lambda p: [1.0], cache_of=lambda: None)
        self._decoded(loader, Path("C:/m/d.mp3"))
        self.assertEqual(loader.request(Path("C:/m/d.mp3")), [1.0])


class PanelToggleTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = _app()

    def panel(self, **settings):
        from player.play_mode_panel import PlayModePanel
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        return p

    def test_it_follows_the_setting_and_defaults_on(self):
        self.assertTrue(self.panel().show_waveform())
        self.assertFalse(self.panel(show_waveform=False).show_waveform())

    def test_flipping_it_tells_the_window(self):
        p = self.panel(show_waveform=True)
        seen = []
        p.waveformToggled.connect(seen.append)
        p.waveform_check.setChecked(False)
        self.assertEqual(seen, [False])

    def test_the_seek_bar_option_is_a_sub_option_of_the_strip(self):
        p = self.panel(show_waveform=True)
        p.show()
        self.assertEqual(p.hide_seek_check.text(), "…replace seek bar")
        self.assertTrue(p.waveform_sub_box.isVisible())
        p.waveform_check.setChecked(False)
        self.assertFalse(p.waveform_sub_box.isVisible())

    def test_the_strip_replaces_the_seek_bar_by_default(self):
        """Shown, the waveform seeks on a click over the same stretch — the
        seek bar under it says nothing new. A saved 'off' stays off."""
        self.assertTrue(self.panel().hide_seek_bar())
        self.assertFalse(self.panel(replace_seek_bar=False).hide_seek_bar())

    def test_an_off_saved_under_the_old_key_does_not_hold(self):
        """`hide_seek_bar` was written on every save while 'off' was the
        default, so its False says nothing about a choice — it is ignored."""
        self.assertTrue(self.panel(hide_seek_bar=False).hide_seek_bar())

    def test_switching_the_strip_on_also_replaces_the_seek_bar(self):
        p = self.panel(show_waveform=False, replace_seek_bar=False)
        p.waveform_check.setChecked(True)
        self.assertTrue(p.hide_seek_bar())

    def test_flipping_the_seek_bar_option_tells_the_window(self):
        p = self.panel(show_waveform=True, replace_seek_bar=False)
        seen = []
        p.seekBarHiddenToggled.connect(seen.append)
        p.hide_seek_check.setChecked(True)
        self.assertEqual(seen, [True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
