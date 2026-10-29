"""Dragging across a playing pad moves it to the spot the played band shows.

Marcel: "for the cartwall pads when i press hold the mouse click and drag i
can fast forward the title to a position indicated by the normal animation
which shows where in the title we are".
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_scrub_"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.audio import cart_voices
from player.widgets import cartwall as gc
from tests.player.test_cartwall_voices import _factory, _pad

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)


class PadScrubTest(unittest.TestCase):
    """✏ off, the pad running: press, drag, let go."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.resize(600, 400)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="C:\\s\\bed.mp3")})])
        self.w.show()
        self.seeks, self.fired = [], []
        self.w.padSeekRequested.connect(lambda k, f: self.seeks.append((k, f)))
        self.w.padClicked.connect(self.fired.append)
        self.b = self.w._buttons[KEY]
        self.y = self.b.height() // 2

    def tearDown(self):
        self.w.deleteLater()

    def at(self, frac):
        return QPoint(int(self.b.width() * frac), self.y)

    def drag(self, start, end, release=True):
        QTest.mousePress(self.b, Qt.MouseButton.LeftButton, pos=self.at(start))
        QTest.mouseMove(self.b, self.at((start + end) / 2))
        QTest.mouseMove(self.b, self.at(end))
        if release:
            QTest.mouseRelease(self.b, Qt.MouseButton.LeftButton, pos=self.at(end))

    def test_the_band_follows_the_mouse_and_the_release_seeks_there(self):
        self.w.set_playing(KEY, True)
        self.w.set_remaining(KEY, 9000, 0.1)
        self.drag(0.1, 0.75, release=False)
        self.assertAlmostEqual(self.b._frac, 0.75, delta=0.02)
        # The player's own tick must not pull the band back mid-drag.
        self.w.set_remaining(KEY, 8900, 0.11)
        self.assertAlmostEqual(self.b._frac, 0.75, delta=0.02)
        QTest.mouseRelease(self.b, Qt.MouseButton.LeftButton, pos=self.at(0.75))
        self.assertEqual(len(self.seeks), 1)
        self.assertEqual(self.seeks[0][0], KEY)
        self.assertAlmostEqual(self.seeks[0][1], 0.75, delta=0.02)
        self.assertEqual(self.fired, [])    # a scrub never stops the pad

    def test_a_drag_back_rewinds(self):
        self.w.set_playing(KEY, True)
        self.w.set_remaining(KEY, 2000, 0.8)
        self.drag(0.8, 0.2)
        self.assertAlmostEqual(self.seeks[0][1], 0.2, delta=0.02)

    def test_past_the_edges_is_the_start_or_the_end(self):
        self.w.set_playing(KEY, True)
        QTest.mousePress(self.b, Qt.MouseButton.LeftButton, pos=self.at(0.5))
        QTest.mouseMove(self.b, QPoint(-40, self.y))
        QTest.mouseRelease(self.b, Qt.MouseButton.LeftButton, pos=QPoint(-40, self.y))
        self.assertEqual(self.seeks, [(KEY, 0.0)])

    def test_after_the_drag_the_tick_moves_the_band_again(self):
        self.w.set_playing(KEY, True)
        self.drag(0.1, 0.6)
        self.w.set_remaining(KEY, 4000, 0.61)
        self.assertAlmostEqual(self.b._frac, 0.61)

    def test_a_plain_click_still_fires(self):
        self.w.set_playing(KEY, True)
        QTest.mouseClick(self.b, Qt.MouseButton.LeftButton, pos=self.at(0.5))
        self.assertEqual(self.fired, [KEY])
        self.assertEqual(self.seeks, [])

    def test_a_pad_that_is_not_playing_does_not_seek(self):
        self.drag(0.1, 0.7)
        self.assertEqual(self.seeks, [])

    def test_a_scrub_is_not_a_ctrl_click(self):
        """Ctrl+drag stays the ▶ queue's toggle on release, not a seek."""
        self.w.set_playing(KEY, True)
        QTest.mousePress(self.b, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.ControlModifier, self.at(0.1))
        QTest.mouseMove(self.b, self.at(0.7))
        QTest.mouseRelease(self.b, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.ControlModifier, self.at(0.7))
        self.assertEqual(self.seeks, [])


class VoiceSeekTest(unittest.TestCase):

    def setUp(self):
        self.v = cart_voices.CartVoices(voices=4, factory=_factory)
        self.v.set_level(1.0)

    def tearDown(self):
        self.v.shutdown()

    def test_seek_moves_the_running_voice(self):
        self.v.fire("a", _pad())
        voice = self.v._voice_for("a")
        self.v.seek("a", 0.5)
        self.assertEqual(voice.player.position(), 5000)

    def test_seek_on_a_silent_pad_does_nothing(self):
        self.v.seek("nobody", 0.5)    # no voice: no error
        self.v.fire("a", _pad())
        voice = self.v._voice_for("a")
        before = voice.player.calls[:]
        self.v.seek("b", 0.5)
        self.assertEqual(voice.player.calls, before)


if __name__ == "__main__":
    unittest.main()
