#!/usr/bin/env python3
"""Every deck remembers its own ⏭ Auto / ✋ Manual.

Run:  py -m unittest tests.gui.test_deck_advance -v

One player, several lists. The Eintanzen panel runs hands-free while the
tournament deck is started title by title, and before this the two shared one
switch — flipping it under the party list flipped it under the round as well.

So the switch answers per deck: it is one of the play values every list
keeps for itself (tests/gui/test_list_play_sets.py has the rest of them, and
the play panel showing the clicked list's).

What plays decides: the deck the evening is currently on is the one whose
answer counts — for walking on to the next title, and for the announcement
that goes with it. ✋ Manual under a deck still silences its announcement, the
way ✋ on the panel always has.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_deckadv_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.playlist_table import PlaylistTable  # noqa: E402
from gui.running_order import Row  # noqa: E402
from player.main_player import PlayerControlMixin  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402
from player.playback_state import PlaybackState  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402


class _Announcer:
    """Records what the hall would have heard."""

    def __init__(self):
        self.spoken = []
        self.speaking = False

    def speak(self, code, takt=None, *, heat=None, now=False):
        self.spoken.append(code)
        return True


class _Desk(PlayerControlMixin):
    """A MainWindow as far as the ⏭/✋ switch reaches into one.

    PlayerControlMixin already carries the pause and Paso Doble mixins, so the
    announcement paths here are the real ones, and the lists are real
    PlaylistTables — the per-list values live on the table itself, so there
    is nothing here for a stand-in to get wrong."""

    def __init__(self, panel, tables=()):
        self._play_panel = panel
        self._all_tables = tuple(tables)
        self._announcer = _Announcer()
        self._between = BetweenDances()
        self._between.announced = False
        self._between.pending = None
        self._playback = PlaybackState()
        self._playback.dance = ""
        self._saves = 0

    def _autosave_playlist(self):
        self._saves += 1

    def _is_playing_mode(self):
        return True


class DeckAdvanceTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def desk(self, *, advance=True, announce=False, decks=2):
        panel = PlayModePanel({"auto_advance": advance,
                               "announce_next": announce})
        self.addCleanup(reap_widget, panel)
        tables = []
        for _ in range(decks):
            t = PlaylistTable()
            self.addCleanup(reap_widget, t)
            tables.append(t)
        desk = _Desk(panel, tables)
        desk._wire_advance_switch()   # the production wiring, not a copy
        for t in tables:
            t.set_advance_toggle(lambda t=t: desk._deck_advance(t),
                                 lambda on, t=t: desk._set_deck_advance(t, on))
            t.set_advance_toggle_visible(True)
        return desk, tables

    # ── the deck's own answer ────────────────────────────────────────────────

    def test_one_deck_switched_by_hand_leaves_the_others_alone(self):
        """The whole point: the party list goes Manual, the round does not."""
        desk, (a, b) = self.desk(advance=True)
        a.advance_toggle().click()
        self.assertFalse(desk._deck_advance(a))
        self.assertTrue(desk._deck_advance(b), "the other deck followed along")
        self.assertIn("Manual", a.advance_toggle().text())
        self.assertIn("Auto", b.advance_toggle().text())

    def test_a_deck_answer_is_worth_saving(self):
        desk, (a, _b) = self.desk()
        a.advance_toggle().click()
        self.assertEqual(desk._saves, 1, "the deck's answer was never saved")

    # ── what plays decides ───────────────────────────────────────────────────

    def playing(self, desk, table, row=0):
        # The play cursor names a placed track: give it a row to play from.
        while len(table._row_meta) <= row:
            table._row_meta.append(Row())
        table._current_play_row = row

    def test_the_playing_deck_is_the_one_asked(self):
        desk, (a, b) = self.desk(advance=True)
        b.advance_toggle().click()                      # b → Manual
        self.playing(desk, a)
        self.assertTrue(desk._playing_advance())
        a._current_play_row = -1
        self.playing(desk, b)
        self.assertFalse(desk._playing_advance())

    def test_nothing_playing_falls_back_to_the_panel(self):
        desk, _t = self.desk(advance=False)
        self.assertFalse(desk._playing_advance())

    # ── the announcement goes with it ────────────────────────────────────────

    def test_a_manual_deck_announces_nothing_at_the_start_of_a_title(self):
        """✋ Manual has always stopped the announcement. Per deck it has to
        stop it for THAT deck — with 🔈 still on for the rest of the evening."""
        desk, (a, _b) = self.desk(advance=True, announce=True)
        desk._playback.dance = "LW"
        a.advance_toggle().click()                      # a → Manual
        self.playing(desk, a)
        desk._maybe_announce_start(None)
        self.assertEqual(desk._announcer.spoken, [])

    def test_an_auto_deck_still_announces(self):
        desk, (a, _b) = self.desk(advance=True, announce=True)
        desk._playback.dance = "LW"
        self.playing(desk, a)
        desk._maybe_announce_start(None)
        self.assertEqual(desk._announcer.spoken, ["LW"])

    def test_a_manual_deck_makes_no_paso_doble_call(self):
        desk, (a, _b) = self.desk(advance=True, announce=True)
        self.playing(desk, a)
        self.assertTrue(desk._pd_call_wanted())
        a.advance_toggle().click()                      # a → Manual
        self.assertFalse(desk._pd_call_wanted())

    # ── which switch counts ──────────────────────────────────────────────────

    def test_the_switch_of_the_list_that_plays_stands_out(self):
        """Every deck has a switch, and only one of them decides what happens
        after the title that is playing. Flipping the one of the deck beside it
        changed nothing on the floor, and looked exactly the same."""
        desk, (a, b) = self.desk()
        desk._big_player = None
        desk._on_list_play(a)
        self.assertTrue(a.advance_toggle().property("live"))
        self.assertFalse(b.advance_toggle().property("live"))
        self.assertIn("playing", a.advance_toggle().toolTip())
        self.assertNotIn("playing", b.advance_toggle().toolTip())
        desk._on_list_play(b)
        self.assertFalse(a.advance_toggle().property("live"))
        self.assertTrue(b.advance_toggle().property("live"))

    def test_the_first_title_of_the_session_marks_its_list(self):
        """At start-up the first title is only cued, and ⏯ on the card (or
        Space, the presenter, the taskbar) starts it without its row's ▶ —
        the path that had marked nothing."""
        from pathlib import Path
        desk, (a, b) = self.desk()
        desk._big_player = None
        desk._cued = True
        desk._playback.path = Path("first.mp3")
        desk._is_player_stopped = lambda: True
        started = []
        desk._play_or_stop = lambda path, start=True: started.append(path)
        self.playing(desk, b)                  # the cue marked b's first row
        self.assertTrue(desk._start_cued())
        self.assertEqual(started, [Path("first.mp3")])
        self.assertTrue(b.advance_toggle().property("live"))
        self.assertFalse(a.advance_toggle().property("live"))

    def test_flipping_the_live_switch_keeps_it_marked(self):
        desk, (a, _b) = self.desk()
        desk._big_player = None
        desk._on_list_play(a)
        a.advance_toggle().click()
        self.assertTrue(a.advance_toggle().property("live"))
        self.assertIn("playing", a.advance_toggle().toolTip())


if __name__ == "__main__":
    unittest.main()
