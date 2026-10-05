#!/usr/bin/env python3
"""🐂 The wait between the call and the first bar of a Paso Doble.

The couples walk on and take position when the dance is called — a PD whose
music starts on the word is danced from the wrong bar. 'Start after: x s' holds
the start back that long. Whether the app makes the call itself is 🔈 Announce
next dance, the same switch as everywhere else; without it the hall's announcer
does and the wait runs silently — counted down on the left Playing panel. ⏯
during the count cuts it short: the couples are in position early.

Run:  py -m unittest tests.player.test_pd_start_hold -v
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_pd_hold_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from player.main_pd import PdStopMixin  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402


class _Panel:
    def __init__(self, delay=5, announce=False, pause=0):
        self._delay = delay
        self._announce = announce
        self._pause = pause

    def pd_start_delay(self):
        return self._delay

    def announce_next(self):
        return self._announce

    def announce_takt(self):
        return False

    def pause_secs(self):
        return self._pause


class _Announcer:
    def __init__(self):
        self.said = []

    def speak(self, dance, takt=None, now=False, heat=None):
        self.said.append((dance, now))


class _Label:
    def __init__(self):
        self.text = ""

    def setText(self, t):
        self.text = t


class _Player:
    def __init__(self):
        self.started = 0

    def play(self):
        self.started += 1


class _Fades:
    def __init__(self):
        self.started = 0

    def start(self):
        self.started += 1


class _Entry:
    bpm = 60


class _Desk(PdStopMixin):
    """Just enough MainWindow for the wait."""

    PATH = Path(r"C:\music\espana.mp3")

    def __init__(self, playing=True, dance="PD", **panel):
        self._playing = playing
        self._playback = PlaybackState()
        self._playback.dance = dance
        self._play_panel = _Panel(**panel)
        self._announcer = _Announcer()
        self._now_playing = _Label()
        self._player = _Player()
        self._fade_timer = _Fades()
        self._playback.token = 7
        self._running = False
        self._countdown = ""
        self._announced_start = 0
        self._pd_hold = None
        self._pd_hold_timer = None

    def _is_playing_mode(self):
        return self._playing

    def _is_player_running(self):
        return self._running

    def _set_countdown(self, text):
        self._countdown = text

    def _playing_row(self):
        return (None, -1)

    def _playing_advance(self):
        # The list in play is on ⏭ Auto. That a ✋ Manual one makes no call is
        # tested against the real mixin in tests/gui/test_deck_advance.py.
        return True

    def _pv(self, key):
        # The playing list's own values; here the panel's stand in for them.
        return {"announce": self._play_panel.announce_next()}[key]

    def _engine_pause_secs(self):
        return self._play_panel.pause_secs()

    def _heat_of(self, _table, _row):
        return None

    def _maybe_announce_start(self, _ent):
        self._announced_start += 1

    def _check_playback(self, _token, _path):
        pass


class _HoldTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def hold(self, d, secs=5.0):
        """Start the wait and make sure its ticker is dropped afterwards — no
        event loop runs here, so it only ever ticks when a test says so."""
        d._hold_pd_start(secs, d.PATH, _Entry())
        self.addCleanup(d._end_pd_hold)
        return d


class PdStartHoldTest(_HoldTest):
    """Who waits, and for how long."""

    def test_a_paso_doble_in_playing_mode_waits(self):
        self.assertEqual(_Desk(delay=5)._pd_start_hold(), 5.0)

    def test_zero_seconds_means_start_at_once(self):
        self.assertEqual(_Desk(delay=0)._pd_start_hold(), 0.0)

    def test_no_other_dance_waits(self):
        self.assertEqual(_Desk(dance="SA", delay=5)._pd_start_hold(), 0.0)

    def test_a_preview_while_planning_starts_at_once(self):
        """Five silent seconds in an audition read as a broken player."""
        self.assertEqual(_Desk(playing=False, delay=5)._pd_start_hold(), 0.0)


class PdCallVoiceTest(_HoldTest):
    """Who makes the call the seconds are counted from — 🔈 Announce next
    dance, no switch of its own."""

    def test_the_announcement_off_means_the_hall_calls_it(self):
        self.assertFalse(_Desk(announce=False)._pd_call_wanted())

    def test_the_announcement_on_means_the_app_calls_it(self):
        self.assertTrue(_Desk(announce=True)._pd_call_wanted())

    def test_the_app_speaks_at_the_head_of_the_wait(self):
        """The bare "Paso Doble", not "Nächster Tanz: …" (`now=True`): the
        couples are already walking on, and this call is the moment the
        seconds are counted from."""
        d = self.hold(_Desk(announce=True))
        self.assertEqual(d._announcer.said, [("PD", True)])

    def test_the_hall_call_leaves_the_app_silent(self):
        d = self.hold(_Desk(announce=False))
        self.assertEqual(d._announcer.said, [])

    def test_a_pause_that_already_announced_it_is_not_repeated(self):
        """`_maybe_announce_next` speaks into the last seconds of the pause —
        the wait then simply follows that call."""
        self.assertFalse(_Desk(announce=True, pause=90)._pd_call_wanted())

    def test_without_a_pause_the_announcement_never_ran(self):
        self.assertTrue(_Desk(announce=True, pause=0)._pd_call_wanted())


class PdHoldDisplayTest(_HoldTest):
    """What the left Playing panel shows while nothing is on the speakers —
    with the call left to the hall there is no sound at all to go by."""

    def test_the_panel_says_what_is_coming_and_when(self):
        d = self.hold(_Desk(), 5.0)
        self.assertIn("Paso Doble", d._countdown)
        self.assertIn("5 s", d._countdown)

    def test_the_card_counts_down_too(self):
        d = self.hold(_Desk(), 5.0)
        self.assertIn("5 s", d._now_playing.text)

    def test_the_seconds_run_down(self):
        d = self.hold(_Desk(), 5.0)
        token, path, _until = d._pd_hold
        d._pd_hold = (token, path, time.monotonic() + 2.0)
        d._pd_hold_tick()
        self.assertIn("2 s", d._countdown)

    def test_no_music_starts_before_the_wait_is_over(self):
        d = self.hold(_Desk(), 5.0)
        self.assertEqual(d._player.started, 0)
        self.assertEqual(d._fade_timer.started, 0)

    def test_the_wait_running_out_starts_the_music(self):
        d = self.hold(_Desk(), 0.0)
        d._pd_hold_tick()
        self.assertEqual(d._player.started, 1)
        self.assertIsNone(d._pd_hold)

    def test_a_stop_during_the_wait_drops_it(self):
        d = self.hold(_Desk(), 5.0)
        d._playback.token += 1          # ■, the next title, another deck
        d._pd_hold_tick()
        self.assertIsNone(d._pd_hold)
        self.assertEqual(d._player.started, 0)


class PdReleaseTest(_HoldTest):
    """The wait is over."""

    def _release(self, d, token=None):
        d._release_held_start(d._playback.token if token is None else token, d.PATH)

    def test_the_music_starts_and_the_card_turns_over(self):
        d = _Desk()
        self._release(d)
        self.assertEqual(d._player.started, 1)
        self.assertEqual(d._fade_timer.started, 1)
        self.assertTrue(d._now_playing.text.startswith("▶"))
        self.assertEqual(d._countdown, "")

    def test_the_dance_is_not_called_a_second_time_over_the_first_bars(self):
        """It was called at the head of the wait — the seconds were counted
        from it. Saying it again once the music runs puts the call after the
        start it announced."""
        d = _Desk(announce=True)
        self.hold(d, 0.0)
        d._pd_hold_tick()
        self.assertEqual(d._announcer.said, [("PD", True)])
        self.assertEqual(d._announced_start, 0)

    def test_a_start_pressed_during_the_wait_is_not_restarted(self):
        d = _Desk()
        d._running = True
        self._release(d)
        self.assertEqual(d._player.started, 0)

    def test_another_title_taking_the_player_cancels_it(self):
        """A stop, the next title or another deck moved the token on — the old
        wait must not start music over what is running now."""
        d = _Desk()
        self._release(d, token=6)
        self.assertEqual(d._player.started, 0)
        self.assertEqual(d._announced_start, 0)

    def test_a_player_that_is_gone_is_not_touched(self):
        d = _Desk()
        d._player = None
        self._release(d)
        self.assertEqual(d._fade_timer.started, 0)


class PdSkipTest(_HoldTest):
    """⏯ while the count runs. The seconds are an estimate of how long the
    couples need; the desk watching them knows better, so the tap ends the
    wait and starts the music there and then."""

    def test_a_tap_starts_the_music_at_once(self):
        d = self.hold(_Desk(), 5.0)
        self.assertTrue(d._skip_pd_hold())
        self.assertEqual(d._player.started, 1)
        self.assertEqual(d._fade_timer.started, 1)

    def test_the_countdown_gives_way_to_the_title(self):
        d = self.hold(_Desk(), 5.0)
        d._skip_pd_hold()
        self.assertEqual(d._countdown, "")
        self.assertTrue(d._now_playing.text.startswith("▶"))

    def test_the_wait_is_gone_and_cannot_start_it_twice(self):
        d = self.hold(_Desk(), 5.0)
        d._skip_pd_hold()
        self.assertIsNone(d._pd_hold)
        d._pd_hold_tick()          # a tick already queued when the tap landed
        self.assertEqual(d._player.started, 1)

    def test_the_dance_is_not_called_again(self):
        """It was called at the head of the wait — cutting the wait short does
        not call it a second time over the music."""
        d = _Desk(announce=True)
        self.hold(d, 5.0)
        d._skip_pd_hold()
        self.assertEqual(d._announcer.said, [("PD", True)])

    def test_a_wait_that_lost_the_player_does_not_swallow_the_tap(self):
        """⏹ or the next title took the player; the wait is only dropped on
        its next tick. A ⏯ inside those 200 ms belongs to whatever is waiting
        now — a 🏁 round-end stop — not to the dead wait."""
        d = self.hold(_Desk(), 5.0)
        d._playback.token += 1
        self.assertFalse(d._skip_pd_hold())
        self.assertIsNone(d._pd_hold)
        self.assertEqual(d._player.started, 0)

    def test_with_no_wait_running_the_tap_is_not_ours(self):
        d = _Desk()
        self.assertFalse(d._skip_pd_hold())
        self.assertEqual(d._player.started, 0)


class ResumeTapTest(unittest.TestCase):
    """What a ⏯ on a standing player means — card, Space, presenter and
    taskbar all arrive here through the big player's `resume_cb`."""

    def desk(self, held, round_pending, cued=False):
        from player.main_player import PlayerControlMixin
        d = PlayerControlMixin.__new__(PlayerControlMixin)
        d.asked = []

        def answer(name, result):
            def f():
                d.asked.append(name)
                return result
            return f

        d._skip_pd_hold = answer("pd", held)
        d._start_next_round = answer("round", round_pending)
        d._start_cued = answer("cued", cued)
        return d

    def test_a_held_paso_doble_takes_the_tap(self):
        d = self.desk(held=True, round_pending=True)
        self.assertTrue(d._resume_tap())
        self.assertEqual(d.asked, ["pd"])

    def test_otherwise_the_next_round_gets_it(self):
        d = self.desk(held=False, round_pending=True)
        self.assertTrue(d._resume_tap())
        self.assertEqual(d.asked, ["pd", "round"])

    def test_then_a_cued_title_gets_it(self):
        d = self.desk(held=False, round_pending=False, cued=True)
        self.assertTrue(d._resume_tap())
        self.assertEqual(d.asked, ["pd", "round", "cued"])

    def test_with_neither_waiting_the_player_keeps_the_tap(self):
        """False → the big player restarts whatever is still loaded."""
        d = self.desk(held=False, round_pending=False)
        self.assertFalse(d._resume_tap())


if __name__ == "__main__":
    unittest.main(verbosity=2)
