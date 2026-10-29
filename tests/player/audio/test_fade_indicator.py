#!/usr/bin/env python3
"""Tests for the ORANGE fade indicator on the big player.

Run:  py -m unittest tests.player.audio.test_fade_indicator -v

A fade-out is the one desk action with no visible side: the volume slides away
over several seconds and the card looks exactly as it did. The end-of-track
warning already blinks the card red, so a running fade blinks it the same beat
in orange — and while both are true the orange wins, because the fade is what
the operator just asked for.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fade_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QWidget

from gui.decks.deck_set import DeckSet
from player.audio.between_dances import BetweenDances
from player.audio.fade_now import FadeNow
from player.audio.mix import OutputMix
from player.audio.playback_state import PlaybackState
from player.widgets.player import BigPlayerWidget
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget

ORANGE = "#fb8c00"
RED = "#e53935"


def _skin(card) -> str:
    """Which skin the card shows: '' plain, 'end' red, 'fade' orange."""
    return card.property("flash")


class _PlayingStub(QMediaPlayer):
    """A player that says it is running: the card only warns about the end of a
    track that is actually playing."""

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState


class FadeBlinkTest(unittest.TestCase):
    """The card itself."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.card = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, self.card)

    def test_the_card_blinks_orange_while_a_fade_runs(self):
        self.card.set_fading(True)
        self.assertTrue(self.card._flash.isActive())
        self.assertEqual(_skin(self.card), "fade")

    def test_the_skins_paint_their_colours(self):
        self.card.resize(320, 240)
        left_edge = (0, 120)

        def border():
            return self.card.grab().toImage().pixelColor(*left_edge).name()
        self.card.set_fading(True)
        self.assertEqual(border(), ORANGE)
        self.card.set_fading(False)
        self.assertNotIn(border(), (ORANGE, RED))

    def test_the_blink_does_not_restyle_the_card(self):
        """A new style sheet re-polishes every child of the card, and the beat
        set one twice a second for the whole final stretch."""
        self.card.set_fading(True)
        calls = []
        self.card.setStyleSheet = calls.append
        self.card._flash_step()
        self.card._flash_step()
        self.assertEqual(calls, [])

    def test_the_blink_alternates_with_the_plain_card(self):
        self.card.set_fading(True)
        self.card._flash_step()
        self.assertEqual(_skin(self.card), "")
        self.card._flash_step()
        self.assertEqual(_skin(self.card), "fade")

    def test_the_fade_colour_wins_over_the_red_end_warning(self):
        """Both can be true at once — the last seconds of a song the operator
        is fading out anyway. Orange is the one that says why."""
        self.card._flash.start()          # as the end warning would
        self.card._flash_on = False
        self.card.set_fading(True)
        self.assertEqual(_skin(self.card), "fade")

    def test_the_end_warning_does_not_stop_the_fade_blink(self):
        """`_update_end_flash` runs on every position tick and stops the blink
        as soon as the song is not in its last seconds — it must leave a
        running fade alone."""
        self.card.set_fading(True)
        self.card._update_end_flash(0, 0)   # nothing playing → no red warning
        self.assertTrue(self.card._flash.isActive())
        self.assertTrue(self.card._fading)

    def test_the_seek_bar_turns_red_even_when_a_fade_started_first(self):
        """The bar marks the final stretch whether or not the beat is already
        running — the fade starts the same timer, and hanging the bar off
        starting it left it blue for the rest of the song."""
        card = BigPlayerWidget(_PlayingStub())
        self.addCleanup(reap_widget, card)
        card.set_fading(True)                 # 🔉↓ before the last seconds
        card._update_end_flash(5_000, 200_000)
        self.assertIn(RED, card._slider.styleSheet())

    def test_the_seek_bar_goes_back_to_blue_after_the_warning(self):
        card = BigPlayerWidget(_PlayingStub())
        self.addCleanup(reap_widget, card)
        card._update_end_flash(5_000, 200_000)
        self.assertIn(RED, card._slider.styleSheet())
        card._update_end_flash(0, 0)          # song over
        self.assertEqual(card._slider.styleSheet(), "")

    def test_the_card_goes_quiet_when_the_fade_ends(self):
        self.card.set_fading(True)
        self.card.set_fading(False)
        self.assertFalse(self.card._flash.isActive())
        self.assertFalse(self.card._fading)
        self.assertEqual(_skin(self.card), "")

    def test_asking_twice_does_not_restart_the_beat(self):
        self.card.set_fading(True)
        self.card._flash_step()             # mid-beat: the plain card shows
        self.card.set_fading(True)
        self.assertEqual(_skin(self.card), "")

    def test_a_card_that_never_faded_is_untouched_by_the_off_switch(self):
        self.card.set_fading(False)
        self.assertFalse(self.card._flash.isActive())
        self.assertEqual(_skin(self.card), "")

    def test_a_stop_on_a_plain_card_leaves_its_style_alone(self):
        """Every halt runs `_stop_end_flash`, right inside the player's stop().
        A re-polish there takes Qt's signal-slot locks while this thread holds
        Python's — and Qt's FFmpeg thread, tearing down the old title at that
        moment, can hold one of those locks while it waits for Python: the
        desk froze for good. A card that is already plain has nothing to undo."""
        repolished, restyled = [], []
        self.card.style = lambda: SimpleNamespace(unpolish=repolished.append,
                                                  polish=lambda w: None)
        self.card._slider.setStyleSheet = restyled.append
        self.card._on_state(QMediaPlayer.PlaybackState.StoppedState)
        self.assertEqual(repolished, [])
        self.assertEqual(restyled, [])

    def test_a_stop_in_the_final_seconds_still_turns_the_card_plain(self):
        card = BigPlayerWidget(_PlayingStub())
        self.addCleanup(reap_widget, card)
        card._update_end_flash(5_000, 200_000)
        self.assertEqual(_skin(card), "end")
        card._on_state(QMediaPlayer.PlaybackState.StoppedState)
        self.assertEqual(_skin(card), "")
        self.assertEqual(card._slider.styleSheet(), "")


class _Card:
    """What the desk mixin is allowed to know about the player card."""

    def __init__(self):
        self.fading = None
        self.paused = None

    def set_fading(self, on):
        self.fading = on

    def set_pause_active(self, on):
        self.paused = on


class _MediaStub:
    def __init__(self):
        self.paused = 0

    def playbackState(self):
        return QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return 0

    def pause(self):
        self.paused += 1


class _Panel:
    def fade_secs(self):
        return 2.0

    def play_set(self):
        return {"fade": 2.0}


class _TimerStub:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def isActive(self):
        return self.running


class _Desk(PlayerControlMixin, QWidget):
    """The fade engine with the media backend, the pause music and the timed
    end stubbed out — all of which have tests of their own."""

    def __init__(self):
        QWidget.__init__(self)
        self._player = _MediaStub()
        self._play_panel = _Panel()
        self._deckset = DeckSet()
        self._deckset.all_tables = ()    # no list: the panel's values are the ones
        self._fade_timer = _TimerStub()
        self._big_player = _Card()
        self._playback = PlaybackState()
        self._playback.path = Path(r"C:\music\WW.mp3")
        self._mix = OutputMix()
        self._fade_now = FadeNow()
        self._fade_now.total = 2.0
        self._between = BetweenDances()
        self._between.pending = None
        self._pd_stop_at = None
        self._ended = []
        self._settings = {}

    def _is_playing_mode(self):
        return True

    def _apply_volume(self):
        pass

    def _set_countdown(self, text):
        pass

    def _maybe_skip_silence(self):
        return False

    def _on_timed_end(self, why):
        self._ended.append(why)


class FadeIndicatorWiringTest(unittest.TestCase):
    """The desk side: whoever starts or ends a fade says so on the card."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.desk = _Desk()
        self.addCleanup(reap_widget, self.desk)

    def test_the_fade_button_lights_it(self):
        self.desk._fade_out_now()
        self.assertTrue(self.desk._big_player.fading)

    def test_the_panic_fade_lights_it_too(self):
        self.desk._fade_and_hold()
        self.assertTrue(self.desk._big_player.fading)

    def test_it_goes_out_when_the_fade_has_run_its_course(self):
        self.desk._fade_out_now()
        self.desk._fade_now.end = time.monotonic() - 0.1   # ramp finished
        self.desk._on_play_tick()
        self.assertEqual(self.desk._ended, ["fade-out finished"])
        self.assertFalse(self.desk._big_player.fading)

    def test_it_goes_out_when_the_panic_fade_reaches_the_hold(self):
        self.desk._fade_and_hold()
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertEqual(self.desk._player.paused, 1)
        self.assertFalse(self.desk._big_player.fading)

    def test_it_keeps_blinking_while_the_ramp_still_runs(self):
        self.desk._fade_out_now()
        self.desk._on_play_tick()
        self.assertTrue(self.desk._big_player.fading)

    def test_stopping_the_engine_clears_it(self):
        """Any other end of the song — a stop, a skip, leaving playing mode —
        goes through `_stop_play_timer`, so the blink cannot outlive the fade."""
        self.desk._fade_out_now()
        self.desk._stop_play_timer()
        self.assertFalse(self.desk._big_player.fading)

    def test_both_fades_run_while_the_desk_shows_planning(self):
        """📱 The phone sends 🔉↓ and 🛑 whichever side the desk shows; the
        desk's own buttons are only on the playing side, so this went unseen:
        the hold started and then nothing drove it, the fade-out did nothing."""
        self.desk._is_playing_mode = lambda: False
        self.desk._fade_and_hold()
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertEqual(self.desk._player.paused, 1)
        self.desk._fade_out_now()
        self.assertIsNotNone(self.desk._fade_now.end)
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertEqual(self.desk._ended, ["fade-out finished"])

    def test_a_second_press_does_not_restart_the_ramp(self):
        """A nervous double 🔉↓: restarting the ramp put the volume back to
        full for a fresh fade (review 2026-10-22, PL2)."""
        self.desk._fade_out_now()
        end = self.desk._fade_now.end
        time.sleep(0.01)
        self.desk._fade_out_now()
        self.assertEqual(self.desk._fade_now.end, end)

    def test_the_fade_button_during_a_panic_fade_ends_the_title(self):
        """🔉↓ on a running 🛑 ramp: the title ends at the bottom instead of
        holding, on the ramp already running."""
        self.desk._fade_and_hold()
        end = self.desk._fade_now.end
        self.desk._fade_out_now()
        self.assertEqual(self.desk._fade_now.end, end)
        self.desk._fade_now.end = time.monotonic() - 0.1
        self.desk._on_play_tick()
        self.assertEqual(self.desk._ended, ["fade-out finished"])
        self.assertEqual(self.desk._player.paused, 0)

    def test_no_card_on_the_desk_is_survived(self):
        self.desk._big_player = None
        self.desk._fade_out_now()
        self.assertIsNotNone(self.desk._fade_now.end)


if __name__ == "__main__":
    unittest.main(verbosity=2)
