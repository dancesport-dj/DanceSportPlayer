#!/usr/bin/env python3
"""A title that will not play hands over to the next one when the evening runs
by itself.

Run:  py -m unittest tests.player.test_playback_failover -v

A playback error used to reset and stop. In Playing mode with ⏭ auto-advance on,
that meant a corrupt or missing file stopped the music on the floor. Now the
failure is logged, the title is remembered as failed (its rows turn red through
the live issue marks until it plays again), a toast names it, and the next title
of the same round starts. The end of a round stays a stop, as it is for a title
that ends normally, and so does 🔁: it would only hand the broken title to itself.
"""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_failover_"))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.main_music import MusicCheckMixin
from player.playback_state import PlaybackState
from tests.player.test_repeat_list import _Desk, _Fixture, _song


class _FailDesk(_Desk):

    def __init__(self, table, playing=True, **settings):
        super().__init__(table, **settings)
        self._playing = playing
        self._playback = PlaybackState()
        self.resets = []

    def _is_playing_mode(self) -> bool:
        return self._playing

    def _reset_playback_ui(self, message: str):
        self.resets.append(message)
        for t in self._deckset.all_tables:
            t.on_playback_stopped()


class FailoverTest(_Fixture):

    def failing_desk(self, row_index: int, playing=True, **settings):
        base = {"auto_advance": True}
        base.update(settings)
        self.deck()                                   # builds self.table
        desk = _FailDesk(self.table, playing=playing, **base)
        rows = self.song_rows()
        row = rows[row_index]
        self.table._current_play_row = row
        path = self.table._row_meta.at(row).entry.path
        desk._player.setSource(QUrl.fromLocalFile(str(path)))
        self.started = []
        self.table._on_play_click = lambda r, p: self.started.append((r, p))
        return desk, rows, path

    def break_play(self, desk):
        with mock.patch("player.main_player._show_toast") as toast:
            desk._on_player_error(None, "Could not decode the file")
            QApplication.processEvents()
        return toast

    def test_the_next_title_of_the_round_starts(self):
        desk, rows, broken = self.failing_desk(0)
        toast = self.break_play(desk)
        nxt = self.table._row_meta.at(rows[1]).entry.path
        self.assertEqual(self.started, [(rows[1], nxt)])
        self.assertEqual(len(desk.resets), 1)
        self.assertIn(broken.stem, toast.call_args.args[1])

    def test_the_failed_title_is_remembered(self):
        desk, _rows, broken = self.failing_desk(0)
        self.break_play(desk)
        self.assertIn(str(broken), desk._playback.failed)
        self.assertIn("Could not decode", desk._playback.failed[str(broken)])

    def test_the_end_of_a_round_stays_a_stop(self):
        desk, _rows, broken = self.failing_desk(1)    # TG 1, Finale follows
        self.break_play(desk)
        self.assertEqual(self.started, [])
        self.assertIn(str(broken), desk._playback.failed)

    def test_without_auto_advance_nothing_starts(self):
        desk, _rows, _p = self.failing_desk(0, auto_advance=False)
        self.break_play(desk)
        self.assertEqual(self.started, [])

    def test_outside_playing_mode_nothing_starts(self):
        desk, _rows, _p = self.failing_desk(0, playing=False)
        self.break_play(desk)
        self.assertEqual(self.started, [])

    def test_a_title_that_loads_again_loses_its_mark(self):
        desk, _rows, broken = self.failing_desk(0)
        self.break_play(desk)
        desk._playback.path = broken
        desk._play_ready_logged = True
        desk._play_t0 = None
        desk._resume_seek_ms = None
        desk._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertNotIn(str(broken), desk._playback.failed)


class FailedTitleIssueTest(unittest.TestCase):
    """The red row: a failed title is one more live Check-Music issue."""

    def check(self, failed):
        class Win(MusicCheckMixin):
            _BEATS_PER_BAR = {"LW": 3, "TG": 2}
            _TEMPO_RATIOS = (1.0, 2.0, 0.5)
            _MIN_PLAY_SECS = 105
            _MAX_PLAY_SECS = 240
            _NOISE_FLOOR_DB = -50.0
            _library = SimpleNamespace(cache=None)
            _settings = {}

        win = Win()
        win._playback = PlaybackState(failed=failed)
        return win._track_issues(_song("LW", 1), probe_silence=False)

    def test_a_failed_title_carries_the_reason(self):
        path = str(_song("LW", 1).path)
        issues = self.check({path: "Could not decode the file"})
        self.assertTrue(any("Could not decode the file" in i for i in issues), issues)

    def test_other_titles_are_untouched(self):
        self.assertEqual(self.check({}), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
