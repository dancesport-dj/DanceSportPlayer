#!/usr/bin/env python3
"""🔁 Endless repeat of the RUNNING title — the loop button on the player card.

Run:  py -m unittest tests.player.test_loop_title -v

Sometimes one title has to keep going: the couples are still on the floor, the
speech is running long, the cake has not arrived. The operator arms the loop and
the title starts over every time it ends, until it is switched off again.

It is a live decision, not a setting: it is not saved anywhere and a restart
finds it off. And it is NOT auto-advance — it holds the evening on one title
instead of walking the list — so it works with ⏭ auto-advance off as well, and
it beats both the 🏁 end of a round and the 🔁 start-over of the whole list.
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
                      tempfile.mkdtemp(prefix="dp_loop_"))

from PySide6.QtMultimedia import QMediaPlayer  # noqa: E402
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

from player.main_player import PlayerControlMixin  # noqa: E402
from player.play_mode_panel import PlayModePanel  # noqa: E402
from player.player import BigPlayerWidget  # noqa: E402
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


class _CardStub:
    """The player card as much as the advance path asks of it — the loop switch
    it is asked for, and the two setters it is told things through."""

    def __init__(self, loop=False):
        self._loop = loop
        self.next_up = []
        self.pause_active = None

    def loop_mode(self) -> bool:
        return self._loop

    def tso_mode(self) -> bool:
        return False

    def set_next_up(self, text: str):
        self.next_up.append(text)

    def set_pause_active(self, on: bool):
        self.pause_active = on


class _Desk(PlayerControlMixin, QWidget):
    """The advance engine with the REAL play panel and the REAL
    `_queue_auto_advance`, with the media backend, the fade timer and the
    player card stubbed out (the shape tests/player/test_party_set.py set)."""

    def __init__(self, table, card, **settings):
        QWidget.__init__(self)
        base = {"auto_advance": True, "pause_enabled": False, "pause_secs": 0}
        base.update(settings)
        self._play_panel = PlayModePanel(base)
        self._all_tables = [table]
        self._big_player = card
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


class LoopButtonTest(unittest.TestCase):
    """The switch itself, on the card's transport row."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def card(self) -> BigPlayerWidget:
        c = BigPlayerWidget(QMediaPlayer())
        self.addCleanup(reap_widget, c)
        return c

    def test_it_starts_out_off(self):
        self.assertFalse(self.card().loop_mode())

    def test_pressing_it_arms_the_loop(self):
        c = self.card()
        c._loop_btn.setChecked(True)
        self.assertTrue(c.loop_mode())

    def test_it_can_be_set_from_outside(self):
        c = self.card()
        c.set_loop_mode(True)
        self.assertTrue(c.loop_mode())
        c.set_loop_mode(False)
        self.assertFalse(c.loop_mode())


class _LoadedPlayer(QMediaPlayer):
    """A player holding a 229 s file. Reloading the SAME file changes no
    source, so Qt sends no second durationChanged — the length is only there
    to be asked for."""

    def duration(self):
        return 229_000


class LoopSeekBarTest(unittest.TestCase):
    """The title comes round again and the seek bar still reaches its end.
    Between the two runs the pause blanks the card, which zeroed the length;
    the reloaded same file never re-announced it, so every drag landed on 0."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_the_seek_bar_spans_the_title_again_after_the_pause(self):
        c = BigPlayerWidget(_LoadedPlayer())
        self.addCleanup(reap_widget, c)
        c._on_duration(229_000)
        c.set_now("LW 1", "LW")
        c.set_now("", status="Auto-advance…")   # the between-titles pause
        c.set_now("LW 1", "LW")                  # 🔁 the same file again
        self.assertEqual(c._slider.maximum(), 229_000)


class LoopEngineTest(unittest.TestCase):
    """What the engine does when a looping title has finished."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def deck(self, loop=True, **settings):
        """Two rounds of two dances: a round seam in the middle and an end to
        run past — the loop has to beat both."""
        self.table = PlaylistTable()
        self.addCleanup(reap_widget, self.table)
        self.table.load(
            {"Vorrunde": [[_song("LW", 1), _song("TG", 1)]],
             "Finale": [[_song("LW", 2), _song("TG", 2)]]},
            ["LW", "TG"],
            [RoundConfig(name="Vorrunde", heats=1, tier="early"),
             RoundConfig(name="Finale", heats=1, tier="final")],
            "S", play_cb=None, suggester=None, use_timbre=False)
        self.card = _CardStub(loop=loop)
        desk = _Desk(self.table, self.card, **settings)
        self.addCleanup(reap_widget, desk)
        return desk

    def song_rows(self) -> list[int]:
        return [r for r, m in enumerate(self.table._row_meta)
                if m and m.entry is not None]

    def test_the_title_arms_itself_again(self):
        desk = self.deck()
        row = self.song_rows()[0]
        self.table._current_play_row = row
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        _t, nrow, _p = desk._between.pending
        self.assertEqual(nrow, row)

    def test_without_the_loop_the_next_title_follows(self):
        desk = self.deck(loop=False)
        rows = self.song_rows()
        self.table._current_play_row = rows[0]
        desk._queue_auto_advance()
        _t, nrow, _p = desk._between.pending
        self.assertEqual(nrow, rows[1])

    def test_it_works_with_auto_advance_switched_off(self):
        """The loop holds the evening on ONE title — it is not the list
        walking on, so it does not need the switch that walks it."""
        desk = self.deck(auto_advance=False)
        row = self.song_rows()[0]
        self.table._current_play_row = row
        desk._queue_auto_advance()
        self.assertIsNotNone(desk._between.pending)
        self.assertEqual(desk._between.pending[1], row)
        self.assertLessEqual(desk._between.advance_at, time.monotonic())

    def test_the_end_of_a_round_does_not_stop_a_looping_title(self):
        desk = self.deck()
        rows = self.song_rows()
        self.table._current_play_row = rows[1]   # last song of the Vorrunde
        desk._queue_auto_advance()
        self.assertIsNone(desk._between.round_start)
        self.assertFalse([c for c in desk.countdowns if "🏁" in c])
        self.assertEqual(desk._between.pending[1], rows[1])

    def test_the_last_title_of_the_list_loops_rather_than_starting_over(self):
        desk = self.deck(repeat_list=True)
        rows = self.song_rows()
        self.table._current_play_row = rows[-1]
        desk._queue_auto_advance()
        self.assertEqual(desk._between.pending[1], rows[-1])

    def test_the_card_says_the_title_comes_again(self):
        desk = self.deck()
        self.table._current_play_row = self.song_rows()[0]
        desk._refresh_next_up()
        self.assertTrue(self.card.next_up, "nothing was put on the card")
        self.assertIn("🔁", self.card.next_up[-1])


if __name__ == "__main__":
    unittest.main()
