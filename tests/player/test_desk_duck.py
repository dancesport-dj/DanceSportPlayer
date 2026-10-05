#!/usr/bin/env python3
"""Tests for the 🔉 duck button (`player.player` cards + `_set_desk_duck`).

Run:  py -m unittest tests.player.test_desk_duck -v

Ducking is what the operator reaches for to talk over the music, so it has to
come down far enough to talk over — 20 %, not the half-volume it used to be —
and the button has to *look* held down while it is on: the emoji alone is far
too small a difference to read across a hall from the desk.

Both player UIs carry the same button, so both are pinned here.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_duck_"))

from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.main_player import _DESK_DUCK  # noqa: E402
from player.player import BigPlayerWidget, PreviewOverlay  # noqa: E402


class DuckFactorTest(unittest.TestCase):

    def test_the_duck_goes_down_to_a_fifth(self):
        """Loud enough to keep the floor moving, quiet enough to talk over."""
        self.assertAlmostEqual(_DESK_DUCK, 0.2)


class _DuckButtonMixin:
    """The same two rules for whichever card `_make()` builds."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.w = self._make()
        self.addCleanup(reap_widget, self.w)

    def test_the_button_stays_pressed_while_ducked(self):
        got = []
        self.w.duckToggled.connect(got.append)
        self.w._duck_btn.click()
        self.assertEqual(got, [True])
        self.w.set_ducked(True)                   # MainWindow reports back
        self.assertTrue(self.w._duck_btn.isChecked())

    def test_it_comes_back_up_when_the_duck_ends(self):
        self.w.set_ducked(True)
        self.w.set_ducked(False)
        self.assertFalse(self.w._duck_btn.isChecked())

    def test_the_click_alone_does_not_leave_it_pressed(self):
        """A checkable button toggles itself on click — but the duck is only
        really on once MainWindow has applied it, so the click must hand the
        state straight back to `_ducked`."""
        self.w._duck_btn.click()                  # nobody listening
        self.assertFalse(self.w._duck_btn.isChecked())


class BigPlayerDuckTest(_DuckButtonMixin, unittest.TestCase):

    def _make(self):
        return BigPlayerWidget(QMediaPlayer())


class PreviewOverlayDuckTest(_DuckButtonMixin, unittest.TestCase):

    def _make(self):
        return PreviewOverlay(QMediaPlayer(), QAudioOutput())


if __name__ == "__main__":
    unittest.main(verbosity=2)
