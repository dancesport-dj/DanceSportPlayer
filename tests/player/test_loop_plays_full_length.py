"""🔁 on the main player: the play length is asked about, "full length" is the default.

Marcel: a looping title that runs 1:30, fades out and starts again makes no
sense - but switching to the play length has to stay possible. So pressing 🔁
while the title has a play length asks: full length (the default, the focused
button) or the configured length. "Full" plays the file to its own end before
it starts again; "configured" cuts and restarts it as before.

The real mixin methods run on a small desk; only the box itself is a stub.
"""
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_loopfull_"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from player.widgets.player import BigPlayerWidget
from player.window.main_play_values import PlayValuesMixin
from player.window.main_player import PlayerControlMixin
from tests.qt_test_support import reap_widget


class _Card:
    """The player card's loop state: the 🔁 button and the answer to the box."""

    def __init__(self):
        self.on = False
        self.cut = False

    def set_loop_cut(self, on):
        self.cut = bool(on)

    def loop_cut(self):
        return self.cut


class _Desk(PlayValuesMixin):
    """What the loop handler and `_play_limit_secs` read, nothing else."""

    _loop_runs_full = PlayerControlMixin._loop_runs_full

    def __init__(self, secs=105, closing=False, pd_run=False):
        self._secs = secs
        self._closing = closing
        self._pd_run = pd_run
        self._card = _Card()
        self._big_player = self._card
        self._playback = SimpleNamespace(dance="LW", runs_to_end=False, path=None)
        self._player = None
        self.asked = []
        self.answer = True
        self.synced = 0

    def press(self, on: bool):
        self._card.on = on
        self._on_loop_mode(on)

    def _looping(self):
        return self._card.on

    def _closing_on_air(self):
        return self._closing

    def _pd_runs_to_its_highlight(self):
        return self._pd_run

    def _playing_row(self):
        return None, -1

    def _engine_list(self):
        return None

    def _dance_secs(self, *a):
        return None

    def _pv(self, key):
        return self._secs if key == "secs" else 0

    def _sync_big_player_limit(self):
        self.synced += 1

    def _ask_loop_full(self, secs) -> bool:
        self.asked.append(secs)
        return self.answer


class LoopPlayLengthTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_without_the_loop_the_play_length_stands(self):
        self.assertEqual(_Desk()._play_limit_secs(), 105)

    def test_pressing_it_asks_with_the_configured_length(self):
        d = _Desk()
        d.press(True)
        self.assertEqual(d.asked, [105])

    def test_full_length_plays_the_title_to_its_end(self):
        d = _Desk()
        d.answer = True
        d.press(True)
        self.assertEqual(d._play_limit_secs(), 0)
        self.assertEqual(d._play_end_secs(), 0)

    def test_the_configured_length_keeps_the_cut(self):
        d = _Desk()
        d.answer = False
        d.press(True)
        self.assertEqual(d._play_limit_secs(), 105)

    def test_the_cut_is_not_enforced_while_the_box_is_open(self):
        """The box runs a nested event loop, the play tick goes on behind it:
        at 1:29 the title must not be cut while the operator reads."""
        d = _Desk()
        seen = []
        d._ask_loop_full = lambda secs: seen.append(d._play_limit_secs()) or True
        d.press(True)
        self.assertEqual(seen, [0])

    def test_releasing_it_brings_the_play_length_back_and_asks_again_next_time(self):
        d = _Desk()
        d.answer = False
        d.press(True)
        d.press(False)
        self.assertEqual(d._play_limit_secs(), 105)
        d.answer = True
        d.press(True)
        self.assertEqual(len(d.asked), 2)
        self.assertEqual(d._play_limit_secs(), 0)

    def test_the_card_is_told_either_way(self):
        d = _Desk()
        d.press(True)
        d.press(False)
        self.assertEqual(d.synced, 2)

    def test_no_play_length_nothing_to_ask(self):
        d = _Desk(secs=0)
        d.press(True)
        self.assertEqual(d.asked, [])
        self.assertEqual(d._play_limit_secs(), 0)

    def test_the_closing_song_and_a_highlight_stop_have_no_length_to_ask_about(self):
        for kw in ({"closing": True}, {"pd_run": True}):
            d = _Desk(**kw)
            d.press(True)
            self.assertEqual(d.asked, [], kw)


class _Player:
    def __init__(self, pos_s, dur_s=200.0):
        self.pos_ms = int(pos_s * 1000)
        self.dur_ms = int(dur_s * 1000)
        self.state = QMediaPlayer.PlaybackState.PlayingState

    def position(self):
        return self.pos_ms

    def duration(self):
        return self.dur_ms

    def playbackRate(self):
        return 1.0

    def playbackState(self):
        return self.state


class _Mix:
    fade = 1.0


class _TickDesk(_Desk):
    """…with a title at `pos_s` of a 200 s file, for the run to its end."""

    _floor_secs_at = PlayerControlMixin._floor_secs_at
    _tick_to_its_end = PlayerControlMixin._tick_to_its_end
    _secs_to_its_end = PlayerControlMixin._secs_to_its_end

    def __init__(self, pos_s, fade=5, **kw):
        super().__init__(**kw)
        self._fade = fade
        self._player = _Player(pos_s)
        self._playback = SimpleNamespace(dance="LW", path="t.mp3", offset_ms=0,
                                         tempo_shift_secs=0.0, runs_to_end=False)
        self._mix = _Mix()
        self.countdown = None
        self.followed = []

    def _pv(self, key):
        return {"secs": self._secs, "fade": self._fade}.get(key, 0)

    def _silence_stop_ms(self):
        return None

    def _hard_end_level(self):
        return 1.0

    def _apply_volume(self):
        pass

    def _follow_fade(self, follow):
        self.followed.append(follow)

    def _set_countdown(self, text):
        self.countdown = text

    def loop_on_full(self):
        self.answer = True
        self.press(True)


class EndlessToItsEndTest(unittest.TestCase):
    """Marcel: "when i activate endless play and answer set to full length the
    title in player is fine but not the time indicator in the playing mode
    controls. when i than remove/disable it and it is over the playing mode
    time it ends abruptly, but in this case i want it to play full end and
    then fade out." """

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    # ===== Acceptance criteria =====

    def test_full_length_counts_down_to_the_titles_own_end(self):
        d = _TickDesk(pos_s=120)
        d.loop_on_full()
        d._tick_to_its_end()
        self.assertEqual(d.countdown, "🔁  1:20")

    def test_off_past_the_play_length_plays_on_to_the_end(self):
        d = _TickDesk(pos_s=120)   # play length 1:45
        d.loop_on_full()
        d.press(False)
        self.assertEqual(d._play_limit_secs(), 0)
        d._tick_to_its_end()
        self.assertEqual(d._mix.fade, 1.0)
        self.assertEqual(d.countdown, "⏳  1:20")

    def test_and_fades_out_over_its_last_seconds(self):
        d = _TickDesk(pos_s=120)
        d.loop_on_full()
        d.press(False)
        d._player.pos_ms = 197_500   # 2.5 s left of a 5 s fade
        d._tick_to_its_end()
        self.assertAlmostEqual(d._mix.fade, 0.5)
        self.assertEqual(d.followed[-1][0], "timed")

    # ===== Core behavior =====

    def test_off_before_the_fade_keeps_the_play_length(self):
        d = _TickDesk(pos_s=60)
        d.loop_on_full()
        d.press(False)
        self.assertEqual(d._play_limit_secs(), 105)

    def test_off_inside_the_fade_plays_on_too(self):
        # Mid-fade (it runs 1:45-1:50), the level would jump to where it had got.
        d = _TickDesk(pos_s=107)
        d.loop_on_full()
        d.press(False)
        self.assertEqual(d._play_limit_secs(), 0)

    def test_off_after_answering_play_length_keeps_the_cut(self):
        d = _TickDesk(pos_s=102)
        d.answer = False
        d.press(True)
        d.press(False)
        self.assertEqual(d._play_limit_secs(), 105)

    def test_no_fade_set_plays_to_the_end_at_full_level(self):
        d = _TickDesk(pos_s=120, fade=0)
        d.loop_on_full()
        d.press(False)
        d._player.pos_ms = 199_000
        d._tick_to_its_end()
        self.assertEqual(d._mix.fade, 1.0)

    def test_a_stopped_deck_is_not_marked(self):
        d = _TickDesk(pos_s=120)
        d.loop_on_full()
        d._player.state = QMediaPlayer.PlaybackState.StoppedState
        d.press(False)
        self.assertFalse(d._playback.runs_to_end)

    # ===== Coverage and null checks =====

    def test_no_play_length_and_no_loop_shows_no_countdown(self):
        d = _TickDesk(pos_s=120, secs=0)
        d._tick_to_its_end()
        self.assertEqual(d.countdown, "")


class LoopBoxTest(unittest.TestCase):
    """The real box, closed by a timer the way a hand would close it."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _ask(self, act):
        """Run the real `_ask_loop_full`; `act(box)` is what the operator does."""
        seen = []

        def operate():
            box = QApplication.activeModalWidget()
            seen.append(box)
            act(box)

        host = QWidget()
        self.addCleanup(reap_widget, host)
        QTimer.singleShot(0, operate)
        result = PlayValuesMixin._ask_loop_full(host, 105)
        return result, seen[0]

    @staticmethod
    def _button(box, word):
        return next(b for b in box.buttons() if word in b.text())

    def test_full_length_is_the_default_and_the_escape(self):
        _, box = self._ask(lambda b: b.defaultButton().click())
        self.assertIn("Full", box.defaultButton().text())
        self.assertIs(box.escapeButton(), box.defaultButton())

    def test_the_other_button_names_the_configured_length(self):
        _, box = self._ask(lambda b: b.defaultButton().click())
        self.assertTrue(any("1:45" in b.text() for b in box.buttons()))

    def test_the_answers(self):
        self.assertTrue(self._ask(lambda b: self._button(b, "Full").click())[0])
        self.assertFalse(self._ask(lambda b: self._button(b, "1:45").click())[0])

    def test_enter_and_escape_both_mean_full_length(self):
        self.assertTrue(self._ask(
            lambda b: QTest.keyClick(b, Qt.Key.Key_Return))[0])
        self.assertTrue(self._ask(
            lambda b: QTest.keyClick(b, Qt.Key.Key_Escape))[0])


class LoopButtonSignalTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_loop_button_tells_the_window(self):
        c = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, c)
        seen = []
        c.loopModeChanged.connect(seen.append)
        c.set_loop_mode(True)
        c.set_loop_mode(False)
        self.assertEqual(seen, [True, False])


if __name__ == "__main__":
    unittest.main()
