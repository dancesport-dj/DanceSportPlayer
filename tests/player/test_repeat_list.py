#!/usr/bin/env python3
"""🔁 Repeat the list: what happens after the LAST title of a running list.

Run:  py -m unittest tests.player.test_repeat_list -v

Auto-advance walks a list to its end and then stops — right for a tournament,
where somebody is standing at the desk anyway. At a party the list is the whole
evening's music and the last title is not meant to be the end of it, so the
list starts again from the top.

It hangs off auto-advance: without it nothing starts by itself, so there is no
end to run past either. And it must not swallow the 🏁 end-of-round stop — that
one happens BETWEEN rounds, long before the last title.
"""

import os
import tempfile
import time
import unittest
from pathlib import Path

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_repeat_"))

from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.main_player import PlayerControlMixin  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402
from gui.playlist_table import PlaylistTable  # noqa: E402
from planner.models import MusicEntry, RoundConfig  # noqa: E402
from player.between_dances import BetweenDances  # noqa: E402
from player.pause_filler import PauseFiller  # noqa: E402


def _song(dance: str, i: int) -> MusicEntry:
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{dance}{i}.mp3"),
                      title=f"{dance} {i}", dance=dance, duration=180)


class _MediaStub:
    """A QMediaPlayer as much as the advance path touches one."""

    def __init__(self):
        self._src = None
        self.played = 0

    def setSource(self, url):
        self._src = url

    def source(self):
        return self._src

    def playbackState(self):
        return QMediaPlayer.PlaybackState.StoppedState

    def setVolume(self, v):
        pass

    def play(self):
        self.played += 1

    def pause(self):
        pass


class _TimerStub:
    def __init__(self):
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def isActive(self) -> bool:
        return self.running


class _Desk(PlayerControlMixin, QWidget):
    """The advance engine with the REAL play panel and the REAL
    `_queue_auto_advance`, with the media backend and the fade timer stubbed
    out (the shape `tests/player/test_party_set.py` established)."""

    def __init__(self, table, **settings):
        QWidget.__init__(self)
        base = {"auto_advance": True, "pause_enabled": False, "pause_secs": 0}
        base.update(settings)
        self._play_panel = PlayModePanel(base)
        self._all_tables = [table]
        self._big_player = None
        self._player = _MediaStub()
        self._pause_player = _MediaStub()
        self._pause_out = _MediaStub()
        self._cache = None          # → _await_loudness has nothing to measure
        self._filler = PauseFiller()
        self._between = BetweenDances()
        self._between.pending = None
        self._between.round_start = None
        self._between.advance_at = 0.0
        self._between.announced = False
        self._between.held = False
        self._between.fade_end = None
        self._fade_now_end = None
        self._announcer = None
        self._fade_timer = _TimerStub()
        self._settings = {}
        self.countdowns = []

    def _is_playing_mode(self) -> bool:
        return True

    def _set_countdown(self, text: str):
        self.countdowns.append(text)

    def _save_play_settings(self):
        pass

    def statusBar(self):
        return self

    def showMessage(self, *a, **kw):
        pass


class _Fixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self, **settings):
        """Two rounds of two dances, so the list carries a real round break in
        the middle AND an end to run past."""
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load(
            {"Vorrunde": [[_song("LW", 1), _song("TG", 1)]],
             "Finale": [[_song("LW", 2), _song("TG", 2)]]},
            ["LW", "TG"],
            [RoundConfig(name="Vorrunde", heats=1, tier="early"),
             RoundConfig(name="Finale", heats=1, tier="final")],
            "S", play_cb=None, suggester=None, use_timbre=False)
        desk = _Desk(self.table, **settings)
        self.addCleanup(reap_widget, desk)
        return desk

    def song_rows(self) -> list[int]:
        return [r for r, m in enumerate(self.table._row_meta)
                if m and m.entry is not None]


class RepeatOptionTest(_Fixture):
    """The switch itself, on the ▶ Playing panel under ⏭ auto-advance."""

    def panel(self, **settings) -> PlayModePanel:
        p = PlayModePanel(settings)
        self.addCleanup(reap_widget, p)
        p.show()
        return p

    def test_a_fresh_install_does_not_repeat(self):
        self.assertFalse(self.panel().repeat_list())

    def test_a_settings_file_that_says_so_starts_it_on(self):
        self.assertTrue(self.panel(auto_advance=True,
                                   repeat_list=True).repeat_list())

    def test_it_leaves_the_panel_without_auto_advance(self):
        """Nothing advances by itself, so there is no end to run past. The tick
        is not greyed out but taken off the panel — it stays where it was set,
        ready for the day ⏭ comes back on."""
        p = self.panel(auto_advance=False, repeat_list=True)
        self.assertFalse(p.repeat_list())
        self.assertTrue(p.repeat_check.isChecked())
        self.assertFalse(p.repeat_check.isVisible())

    def test_switching_auto_advance_on_brings_it_back(self):
        p = self.panel(auto_advance=False, repeat_list=True)
        p.advance_check.setChecked(True)
        self.assertTrue(p.repeat_check.isVisible())
        self.assertTrue(p.repeat_list())

    def test_switching_auto_advance_off_and_on_keeps_the_tick(self):
        """The round trip must not cost the setting — it is only hidden."""
        p = self.panel(auto_advance=True, repeat_list=True)
        p.advance_check.setChecked(False)
        p.advance_check.setChecked(True)
        self.assertTrue(p.repeat_check.isChecked())
        self.assertTrue(p.repeat_list())
        self.assertTrue(p.repeat_setting_on())


class RepeatEngineTest(_Fixture):
    """What the engine does when the last title of the list has finished."""

    def test_the_list_ends_when_the_switch_is_off(self):
        desk = self.deck(repeat_list=False)
        self.table._current_play_row = self.song_rows()[-1]
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.pending)

    def test_the_last_title_arms_the_first_one_again(self):
        desk = self.deck(repeat_list=True)
        rows = self.song_rows()
        self.table._current_play_row = rows[-1]
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        _t, nrow, _p = desk._between.pending
        self.assertEqual(nrow, rows[0])

    def test_starting_over_is_not_read_as_the_end_of_a_round(self):
        """The first title sits in another round than the last one, so the
        round-change test would otherwise stop the evening with a 🏁."""
        desk = self.deck(repeat_list=True)
        self.table._current_play_row = self.song_rows()[-1]
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertIsNone(desk._between.round_start)
        self.assertFalse([c for c in desk.countdowns if "🏁" in c])
        self.assertLessEqual(desk._between.advance_at, time.monotonic())

    def test_a_round_break_still_stops_the_evening(self):
        """Mid-list nothing changes: the round ends, the operator starts the
        next one. Repeat only speaks at the very end."""
        desk = self.deck(repeat_list=True)
        rows = self.song_rows()
        self.table._current_play_row = rows[1]   # last song of the Vorrunde
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.pending)
        self.assertIsNotNone(desk._between.round_start)
        self.assertTrue([c for c in desk.countdowns if "🏁" in c])


if __name__ == "__main__":
    unittest.main()
