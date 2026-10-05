#!/usr/bin/env python3
"""⏳ The call before the first bar, instead of over it.

Run:  py -m unittest tests.player.test_announce_wait -v

Without a pause there is no gap the announcement can run in, so the dance is
named over the first bars with the music ducked under it. In a hall that reads
as two things at once: "Langsamer Walzer" and the Langsamer Walzer, talking
over each other.

⏳ on the play panel turns that round — the dance is called into silence and
the music follows when the voice is done. Nothing counts down while it waits:
the hall hears the call, then the music, which is the whole point of asking
for it.

With a pause configured nothing here applies: the call goes into the pause and
`_hold_for_announcement` already keeps the music off its last word.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_annwait_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.running_order import Row  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402


class _Announcer:
    def __init__(self, works=True):
        self.spoken = []
        self.speaking = False
        self._works = works

    def speak(self, code, takt=None, *, heat=None, now=False):
        if not self._works:
            return False
        self.spoken.append((code, now))
        self.speaking = True
        return True


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


class _Label:
    def __init__(self):
        self.text = ""

    def setText(self, t):
        self.text = t


class _Entry:
    bpm = 29


class _Desk(PlayerControlMixin):
    """A MainWindow as far as the start call reaches into one."""

    PATH = Path(r"C:\music\walzer.mp3")

    def __init__(self, panel, table, announcer):
        self._play_panel = panel
        self._all_tables = (table,)
        self._announcer = announcer
        self._playback = PlaybackState()
        self._playback.dance = "LW"
        self._between = BetweenDances()
        self._between.pending = None
        self._between.quiet_until = 0.0
        self._playback.token = 4
        self._player = _Player()
        self._fade_timer = _Fades()
        self._now_playing = _Label()
        self._countdown = ""
        self._running = False
        self._checked = []

    def _is_playing_mode(self):
        return True

    def _is_player_running(self):
        return self._running

    def _set_countdown(self, text):
        self._countdown = text

    def _check_playback(self, token, path):
        self._checked.append((token, path))


class AnnounceWaitTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desk(self, *, wait=True, announce=True, pause=False, works=True):
        panel = PlayModePanel({"auto_advance": True,
                               "announce_next": announce,
                               "announce_wait": wait,
                               "pause_enabled": pause,
                               "pause_secs": 15})
        self.addCleanup(reap_widget, panel)
        table = PlaylistTable()
        self.addCleanup(reap_widget, table)
        table._row_meta.append(Row())   # the play cursor names a placed track
        table._current_play_row = 0
        return _Desk(panel, table, _Announcer(works)), table

    # ── the switch itself ────────────────────────────────────────────────────

    def test_the_pair_belongs_to_the_announcement_not_to_auto_advance(self):
        """It sat indented under ⏭ Auto-advance, which is not what it answers.

        Whether the call runs over the first bars or before them is a
        question about the CALL, and there is no call at all unless 🔈
        Announce next dance is on — so it hides with the rest of the
        announcement settings and shows with them.
        """
        off = PlayModePanel({"announce_next": False, "auto_advance": True})
        self.addCleanup(reap_widget, off)
        off.show()
        self.assertFalse(off.announce_over_radio.isVisible(),
                         "the pair is on screen with nothing to announce")

        on = PlayModePanel({"announce_next": True, "auto_advance": True})
        self.addCleanup(reap_widget, on)
        on.show()
        self.assertTrue(on.announce_over_radio.isVisible())
        self.assertTrue(on.announce_wait_radio.isVisible())

    def test_the_pair_follows_the_announcement_switch(self):
        panel = PlayModePanel({"announce_next": True})
        self.addCleanup(reap_widget, panel)
        panel.show()
        panel.announce_check.setChecked(False)
        self.assertFalse(panel.announce_wait_radio.isVisible())
        panel.announce_check.setChecked(True)
        self.assertTrue(panel.announce_wait_radio.isVisible())

    def test_the_panel_starts_on_the_old_behaviour(self):
        """A hall that never asked keeps hearing what it heard yesterday."""
        panel = PlayModePanel({})
        self.addCleanup(reap_widget, panel)
        self.assertFalse(panel.announce_wait())
        self.assertTrue(panel.announce_over_radio.isChecked())

    def test_the_answer_comes_back_from_the_settings(self):
        desk, _t = self.desk(wait=True)
        self.assertTrue(desk._play_panel.announce_wait())

    # ── which of the two the start takes ─────────────────────────────────────

    def test_over_the_first_bars_holds_nothing_back(self):
        desk, _t = self.desk(wait=False)
        self.assertFalse(desk._announce_start_first(_Entry()))
        self.assertEqual(desk._announcer.spoken, [],
                         "the call was made before the music after all")
        desk._maybe_announce_start(_Entry())
        self.assertEqual(desk._announcer.spoken, [("LW", True)])

    def test_waiting_calls_the_dance_before_the_music(self):
        desk, _t = self.desk(wait=True)
        self.assertTrue(desk._announce_start_first(_Entry()))
        self.assertEqual(desk._announcer.spoken, [("LW", True)])
        desk._maybe_announce_start(_Entry())
        self.assertEqual(desk._announcer.spoken, [("LW", True)],
                         "the dance was named a second time over the music")

    def test_a_pause_announces_into_the_pause_as_before(self):
        """There the call has a gap of its own and the music is already held
        off its last word — nothing to turn round."""
        desk, _t = self.desk(wait=True, pause=True)
        self.assertFalse(desk._announce_start_first(_Entry()))
        self.assertEqual(desk._announcer.spoken, [])

    def test_nothing_waits_for_a_call_that_is_switched_off(self):
        desk, _t = self.desk(wait=True, announce=False)
        self.assertFalse(desk._announce_start_first(_Entry()))
        self.assertEqual(desk._announcer.spoken, [])

    def test_a_manual_list_neither_calls_nor_waits(self):
        desk, table = self.desk(wait=True)
        desk._list_vals(table)["advance"] = False
        self.assertFalse(desk._announce_start_first(_Entry()))
        self.assertEqual(desk._announcer.spoken, [])

    def test_a_call_that_could_not_be_made_does_not_hold_the_music(self):
        """No speech engine and no clips: the title must start, not sit in a
        wait for a voice that is never coming."""
        desk, _t = self.desk(wait=True, works=False)
        self.assertFalse(desk._announce_start_first(_Entry()))

    # ── the wait ─────────────────────────────────────────────────────────────

    def test_the_music_stays_off_while_the_voice_runs(self):
        desk, _t = self.desk(wait=True)
        desk._announce_start_first(_Entry())
        desk._wait_for_announcement(desk.PATH)
        self.assertEqual(desk._player.started, 0)
        self.assertEqual(desk._fade_timer.started, 0)
        self.assertEqual(desk._countdown, "", "the wait counted down at the hall")

    def test_the_music_starts_once_the_voice_is_done(self):
        desk, _t = self.desk(wait=True)
        desk._announce_start_first(_Entry())
        desk._wait_for_announcement(desk.PATH)
        desk._announcer.speaking = False
        desk._between.quiet_until = time.monotonic() - 0.01   # the tail is up
        desk._poll_announcement(desk._playback.token, desk.PATH)
        self.assertEqual(desk._player.started, 1)
        self.assertEqual(desk._fade_timer.started, 1)
        self.assertIn("walzer", desk._now_playing.text,
                      "the card was left standing in the wait")

    def test_the_last_word_is_not_stepped_on(self):
        """The tail: the hall should hear the call end, not have the title come
        in on it. Same wait the pause gives the voice."""
        desk, _t = self.desk(wait=True)
        desk._announce_start_first(_Entry())
        desk._wait_for_announcement(desk.PATH)
        desk._announcer.speaking = False          # …but the tail is still running
        desk._poll_announcement(desk._playback.token, desk.PATH)
        self.assertEqual(desk._player.started, 0)

    def test_the_silence_after_the_last_word_is_a_breath_not_a_hole(self):
        """The hall reported the gap as too long to sit through.

        The wait was borrowing the pause's tail, 1.2s, which is right where
        it belongs: in a pause there is filler music underneath and 1.2s of
        it is inaudible. Here there is nothing underneath — the room is
        silent from the last word until the first bar, and 1.2s of silence
        in a hall is a hole. The start path gets its own, shorter tail.

        0.5 was the bound the first nudge (1.2 → 0.35) had to clear. The hall
        heard that one as a wait too, so the tail is 0.20 and the bound comes
        down with it — a tail that creeps back up is the defect.
        """
        desk, _t = self.desk(wait=True)
        desk._announce_start_first(_Entry())
        t0 = time.monotonic()
        desk._wait_for_announcement(desk.PATH)
        self.assertLessEqual(desk._between.quiet_until - t0, 0.25)

    def test_the_pause_keeps_the_tail_it_always_had(self):
        """Nothing was wrong with the pause, and filler music covers it."""
        from player.main_pause import _ANNOUNCE_TAIL
        self.assertEqual(_ANNOUNCE_TAIL, 1.2)

    def test_a_stop_during_the_wait_leaves_the_music_alone(self):
        desk, _t = self.desk(wait=True)
        desk._announce_start_first(_Entry())
        desk._wait_for_announcement(desk.PATH)
        desk._announcer.speaking = False
        desk._between.quiet_until = time.monotonic() - 0.01
        desk._playback.token += 1                     # ■, or the next title
        desk._poll_announcement(4, desk.PATH)
        self.assertEqual(desk._player.started, 0)


if __name__ == "__main__":
    unittest.main()
