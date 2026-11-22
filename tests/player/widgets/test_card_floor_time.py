"""The card's time labels in floor time: with the tempo fader off zero, the
⏳ end, the elapsed and the -remaining say how long the couples dance, not
where the cut lands in the file. At −16 % a 1:30 play length is 1:15.6 of
file — the card said 01:15 and the operator read it as a shortened title."""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_card_floor_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from player.widgets.player import BigPlayerWidget
from tests.qt_test_support import reap_widget


class _Player(QMediaPlayer):
    """A deck at a set rate and position, nothing loaded."""

    def __init__(self, rate: float, pos: int):
        super().__init__()
        self._rate, self._pos = rate, pos

    def playbackRate(self):
        return self._rate

    def position(self):
        return self._pos


class CardFloorTimeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _card(self, rate: float, pos: int, dur: int = 200_000):
        card = BigPlayerWidget(_Player(rate, pos))
        self.addCleanup(reap_widget, card)
        card._dur = dur
        return card

    # ===== Acceptance criteria =====

    def test_the_cut_reads_as_the_play_length_at_minus_16(self):
        card = self._card(0.84, 0)
        card.set_limit(75_600)
        self.assertIn("01:30 /", card._limit_lbl.text())

    def test_the_cut_reads_as_the_play_length_at_plus_16(self):
        card = self._card(1.16, 0)
        card.set_limit(104_400)
        self.assertIn("01:30 /", card._limit_lbl.text())

    def test_remaining_is_what_the_floor_still_hears(self):
        card = self._card(0.84, 50_400)   # 60 s danced at 0.84
        card.set_limit(75_600)            # 1:30 on the floor
        self.assertEqual(card._remaining.text(), "-00:30")
        self.assertEqual(card._elapsed.text(), "01:00")

    # ===== Core behavior =====

    def test_the_window_says_what_was_danced_before_a_tempo_change(self):
        # 60 s at normal tempo, then −16 %: the window books the history.
        card = self._card(0.84, 60_000)
        card.floor_secs_at = lambda pos: 60.0 + (pos - 60_000) / 1000 / 0.84
        card.set_limit(60_000 + 25_200)   # 30 s more at 0.84
        self.assertIn("01:30 /", card._limit_lbl.text())
        self.assertEqual(card._elapsed.text(), "01:00")
        self.assertEqual(card._remaining.text(), "-00:30")

    def test_normal_tempo_is_file_time(self):
        card = self._card(1.0, 30_000)
        card.set_limit(90_000)
        self.assertIn("01:30 / 03:20", card._limit_lbl.text())
        self.assertEqual(card._elapsed.text(), "00:30")


if __name__ == "__main__":
    unittest.main()
