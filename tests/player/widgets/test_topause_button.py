"""☕ Jump to the pause, under the player card's transport.

Run:  .venv\\Scripts\\python.exe -m unittest tests.player.widgets.test_topause_button -v

With "Pause between songs" off there is no pause to jump into. The button used
to stay there greyed out; a tester asked for it to go, so it does — and comes
back with the pause.
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_topause_"))

from PySide6.QtMultimedia import QMediaPlayer

from player.widgets.player import BigPlayerWidget
from tests.qt_test_support import qapp, reap_widget


class ToPauseButtonTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        qapp()

    def card(self) -> BigPlayerWidget:
        c = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, c)
        c.set_now("LW 1", "LW")   # a title is up: the aux row shows
        return c

    def test_it_shows_while_a_pause_can_follow(self):
        c = self.card()
        c.set_pause_available(True)
        self.assertFalse(c._topause_btn.isHidden())

    def test_it_is_gone_while_the_pause_is_off(self):
        c = self.card()
        c.set_pause_available(False)
        self.assertTrue(c._topause_btn.isHidden())
        # A new title on the card must not bring it back.
        c.set_now("TG 1", "TG")
        self.assertTrue(c._topause_btn.isHidden())
        # …and the fade-out next to it stays.
        self.assertFalse(c._fade_btn.isHidden())

    def test_it_comes_back_with_the_pause(self):
        c = self.card()
        c.set_pause_available(False)
        c.set_pause_available(True)
        self.assertFalse(c._topause_btn.isHidden())


if __name__ == "__main__":
    unittest.main()
