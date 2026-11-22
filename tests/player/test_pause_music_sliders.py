"""🎶 The big player's volume and tempo sliders grey out while the pause music
plays between two titles.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_pause_music_sliders -v

The pause music is a cartwall pad (a 🎶 background pad from the ▶ queue, or
an endless pad) playing while the deck is stopped. Pads follow their own
fader (Mix.cartwall), never the music fader, and have no tempo: the two
sliders would move nothing. Marcel: "while playing pause music the volume
slider and pitch slider on the main player does not work, so grey them out".
"""
import os
import sys
import tempfile
import unittest
from typing import Any

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pause_sliders_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from planner.playing.cartwall import CartPad, Page
from player.widgets import cartwall as gc
from player.widgets.player import BigPlayerWidget
from tests.player.test_cartwall_queue import _Desk, _samples
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

STOPPED = QMediaPlayer.PlaybackState.StoppedState
PLAYING = QMediaPlayer.PlaybackState.PlayingState


class _Deck:
    def __init__(self):
        self.state = STOPPED

    def playbackState(self):
        return self.state


class _Card:
    def __init__(self):
        self.calls = []

    def set_pause_music(self, on):
        self.calls.append(on)


class _Case(unittest.TestCase):
    """A wall with a 🎶 background pad, an endless pad and a plain pad."""

    def setUp(self):
        files = _samples("bed", "loop", "jingle")
        page = Page(pads={(0, 0): CartPad(path=files["bed"], background=True),
                          (0, 1): CartPad(path=files["loop"], loop=True),
                          (1, 0): CartPad(path=files["jingle"])})
        self.w = gc.CartwallWidget()
        self.addCleanup(reap_widget, self.w)
        self.w.set_wall((2, 2), [page])
        self.desk: Any = _Desk(self.w)
        self.v = self.desk._cart_voices
        self.addCleanup(self.v.shutdown)
        self.desk._player = _Deck()
        self.desk._big_player = self.card = _Card()

    def play(self, cell):
        key = (0,) + cell
        self.v.fire(key, self.w.pad_at(key))
        self.desk._sync_pause_music()

    def locked(self):
        return self.card.calls[-1]


class PauseMusicSlidersTest(_Case):

    # ===== Acceptance criteria =====

    def test_a_background_pad_with_the_deck_stopped_greys_them(self):
        self.play((0, 0))
        self.assertTrue(self.locked())

    def test_an_endless_pad_with_the_deck_stopped_greys_them(self):
        self.play((0, 1))
        self.assertTrue(self.locked())

    def test_the_next_title_brings_them_back(self):
        self.play((0, 0))
        self.desk._player.state = PLAYING
        self.desk._cart_follow_deck(PLAYING)
        self.assertFalse(self.locked())

    def test_the_pause_music_stopping_brings_them_back(self):
        self.play((0, 0))
        self.v.stop((0, 0, 0))
        self.v._finish_fade(self.v._voice_for((0, 0, 0)))
        self.desk._sync_pause_music()
        self.assertFalse(self.locked())

    # ===== Core behavior =====

    def test_a_plain_pad_is_no_pause_music(self):
        self.play((1, 0))
        self.assertFalse(self.locked())

    def test_a_bed_under_a_playing_title_leaves_them_on(self):
        self.desk._player.state = PLAYING
        self.play((0, 0))
        self.assertFalse(self.locked())

    def test_the_pad_count_changing_asks_again(self):
        self.desk._on_cart_active(1)
        self.assertEqual(self.card.calls, [False])

    # ===== Coverage and null checks =====

    def test_no_big_player_is_no_error(self):
        self.desk._big_player = None
        self.play((0, 0))


class BigPlayerPauseMusicTest(unittest.TestCase):

    def setUp(self):
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)

    def sliders(self):
        c = self.card
        return (c._vol, c._vol_down_btn, c._vol_up_btn, c._vol_lbl,
                c._tempo, c._tempo_down_btn, c._tempo_up_btn)

    # ===== Acceptance criteria =====

    def test_on_greys_volume_and_tempo(self):
        self.card.set_pause_music(True)
        self.assertFalse(any(w.isEnabled() for w in self.sliders()))

    def test_off_gives_them_back(self):
        self.card.set_pause_music(True)
        self.card.set_pause_music(False)
        self.assertTrue(all(w.isEnabled() for w in self.sliders()))

    def test_greyed_out_looks_different(self):
        """Marcel: "the grey out faders are not visible distinguishable to be
        deactivated" - the card's skin painted them the same either way."""
        self.card.resize(420, 400)
        self.card.show()
        self.card._vol.setValue(60)
        self.card._tempo.setValue(50)
        QApplication.processEvents()
        before = [w.grab().toImage() for w in (self.card._vol, self.card._tempo)]
        self.card.set_pause_music(True)
        QApplication.processEvents()
        after = [w.grab().toImage() for w in (self.card._vol, self.card._tempo)]
        for b, a in zip(before, after, strict=True):
            self.assertNotEqual(b, a)

    # ===== Core behavior =====

    def test_the_tooltip_says_why(self):
        tip = self.card._vol.toolTip()
        self.card.set_pause_music(True)
        self.assertIn("pause music", self.card._vol.toolTip())
        self.assertIn("pause music", self.card._tempo.toolTip())
        self.assertIn("level", self.card._vol.toolTip())
        self.assertIn("own tempo", self.card._tempo.toolTip())
        self.assertNotIn("level", self.card._tempo.toolTip())
        self.card.set_pause_music(False)
        self.assertEqual(self.card._vol.toolTip(), tip)

    def test_the_rest_of_the_card_stays_usable(self):
        self.card.set_pause_music(True)
        self.assertTrue(self.card._panic_btn.isEnabled())
        self.assertTrue(self.card._duck_btn.isEnabled())

    def test_the_duck_tooltip_says_it_ducks_the_pause_music(self):
        """Marcel kept 🔉 working on the pause music (it lowers the pads too,
        Mix.cartwall × desk_level); its tooltip says so meanwhile."""
        self.card.set_duck_level(30)
        tip = self.card._duck_btn.toolTip()
        self.card.set_pause_music(True)
        self.assertIn("30", self.card._duck_btn.toolTip())
        self.assertIn("pause music", self.card._duck_btn.toolTip())
        self.card.set_duck_level(40)
        self.assertIn("pause music", self.card._duck_btn.toolTip())
        self.card.set_pause_music(False)
        self.card.set_duck_level(30)
        self.assertEqual(self.card._duck_btn.toolTip(), tip)


if __name__ == "__main__":
    unittest.main()
