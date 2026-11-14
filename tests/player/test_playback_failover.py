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
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_failover_"))

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication

from gui.window.main_music import MusicCheckMixin
from player.audio.playback_state import PlaybackState
from tests.player.audio.test_repeat_list import _Desk, _Fixture, _MediaStub, _song


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
        with mock.patch("player.window.main_load.show_toast") as toast:
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
        desk._playback.ready_logged = True
        desk._resume_seek_ms = None
        desk._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
        self.assertNotIn(str(broken), desk._playback.failed)


class _LengthStub(_MediaStub):
    """A backend that took the file for something else: it reports `duration`
    and sits at its end."""

    def __init__(self, duration):
        super().__init__()
        self._duration = duration

    def duration(self):
        return self._duration

    def position(self):
        return self._duration


class EndedBeforeItBeganTest(_Fixture):
    """Marcel: a title that plays in Explorer was skipped without a word. The
    backend (ffmpeg) took the file for an MPEG program stream, gave it a length
    of 77 677 s and reported "end of file" at once and without an error — which
    the player met as a title that ended by itself."""

    failing_desk = FailoverTest.failing_desk

    def stand(self, backend_ms, since_play=0.5, row=0):
        """A title `since_play` s into its load that the backend measures at
        `backend_ms` (the library says 180 s)."""
        desk, rows, path = self.failing_desk(row)
        desk._player = _LengthStub(backend_ms)
        entry = self.table._row_meta.at(rows[row]).entry
        desk._library = SimpleNamespace(
            cache=None, lib=SimpleNamespace(entry_for=lambda p: entry))
        desk._playback.path = path
        desk._resume_seek_ms = None
        desk._playback.play_t0 = time.perf_counter() - since_play
        return desk, rows, path

    def end_at_once(self, backend_ms, row=0):
        desk, rows, path = self.stand(backend_ms, row=row)
        with mock.patch("player.window.main_load.show_toast"),                 mock.patch("player.window.main_player.show_toast") as toast:
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            self.settle(desk)
        return desk, rows, path, toast

    @staticmethod
    def settle(desk):
        """Wait for the repair worker and deliver its answer."""
        from player.window.main_audio import pendingWork
        for w in list(pendingWork(desk).repairs.values()):
            w.wait(5000)
        QApplication.processEvents()      # the answer
        QApplication.processEvents()      # what it scheduled (the next title)

    def test_a_length_far_off_the_librarys_at_once_is_a_failure(self):
        desk, rows, path, _toast = self.end_at_once(77_677_747)
        self.assertIn(str(path), desk._playback.failed)
        self.assertEqual(len(desk.resets), 1)

    def test_the_next_title_of_the_round_starts_after_it(self):
        _desk, rows, _path, _toast = self.end_at_once(77_677_747)
        nxt = self.table._row_meta.at(rows[1]).entry.path
        self.assertEqual(self.started, [(rows[1], nxt)])

    def test_the_toast_names_the_title_and_the_way_out(self):
        # the end of a round: no failover, so the toast is this one's
        with mock.patch.dict(os.environ, {"QT_MEDIA_BACKEND": "ffmpeg"}):
            _desk, _rows, path, toast = self.end_at_once(77_677_747, row=1)
        self.assertIn(path.stem, toast.call_args.args[1])
        self.assertIn("Audio backend", toast.call_args.args[1])

    def test_the_first_time_it_is_replayed_from_a_repaired_copy(self):
        desk, _rows, path = self.stand(77_677_747)
        copy = path.with_name("repaired.mp3")
        desk._play_or_stop = mock.Mock()
        with mock.patch("player.window.main_player.repaired_copy",
                        return_value=copy), \
                mock.patch("player.window.main_player.show_toast"):
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            self.settle(desk)
        self.assertEqual(desk._playback.repaired[str(path)], copy)
        desk._play_or_stop.assert_called_once_with(path)
        self.assertNotIn(str(path), desk._playback.failed)
        self.assertEqual(desk.resets, [])

    def test_a_title_whose_copy_ends_at_once_too_is_a_failure(self):
        desk, _rows, path = self.stand(77_677_747)
        desk._playback.repaired[str(path)] = path.with_name("repaired.mp3")
        desk._play_or_stop = mock.Mock()
        with mock.patch("player.window.main_player.repaired_copy") as repair, \
                mock.patch("player.window.main_player.show_toast"), \
                mock.patch("player.window.main_load.show_toast"):
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            QApplication.processEvents()
        repair.assert_not_called()
        desk._play_or_stop.assert_not_called()
        self.assertIn(str(path), desk._playback.failed)

    def test_a_file_that_cannot_be_repaired_is_a_failure(self):
        desk, _rows, path = self.stand(77_677_747)
        desk._play_or_stop = mock.Mock()
        with mock.patch("player.window.main_player.repaired_copy",
                        return_value=None), \
                mock.patch("player.window.main_player.show_toast"), \
                mock.patch("player.window.main_load.show_toast"):
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            self.settle(desk)
        desk._play_or_stop.assert_not_called()
        self.assertIn(str(path), desk._playback.failed)

    def test_the_copy_is_made_off_the_gui_thread(self):
        """Review F3: the repair read and wrote the whole file on the GUI
        thread, a freeze for a large title on a slow drive."""
        import threading
        desk, _rows, path = self.stand(77_677_747)
        desk._play_or_stop = mock.Mock()
        threads = []

        def repair(_src):
            threads.append(threading.current_thread())
            return path.with_name("repaired.mp3")
        with mock.patch("player.window.main_player.repaired_copy", repair), \
                mock.patch("player.window.main_player.show_toast"):
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            self.settle(desk)
        self.assertEqual(len(threads), 1)
        self.assertIsNot(threads[0], threading.main_thread())
        desk._play_or_stop.assert_called_once_with(path)

    def test_a_copy_that_lands_after_another_title_started_is_kept_quiet(self):
        desk, _rows, path = self.stand(77_677_747)
        desk._play_or_stop = mock.Mock()
        with mock.patch("player.window.main_player.repaired_copy",
                        return_value=path.with_name("repaired.mp3")), \
                mock.patch("player.window.main_player.show_toast"), \
                mock.patch("player.window.main_load.show_toast"):
            desk._on_media_status(QMediaPlayer.MediaStatus.EndOfMedia)
            desk._playback.token += 1                 # ⏭ while it was copying
            self.settle(desk)
        desk._play_or_stop.assert_not_called()
        self.assertNotIn(str(path), desk._playback.failed)
        self.assertEqual(desk.resets, [])

    def test_the_backend_opens_the_copy_not_the_original(self):
        from player.window.main_load import TrackLoadMixin
        desk, _rows, path = self.stand(180_000)
        copy = path.with_name("repaired.mp3")
        desk._playback.repaired[str(path)] = copy
        desk._settings = {}
        url = TrackLoadMixin._source_url(desk, path)
        self.assertEqual(Path(url.toLocalFile()), copy)

    def test_a_copy_made_in_an_earlier_session_is_opened_at_once(self):
        """Marcel: loading one of the two problem titles still skipped. The copy
        was on disk, but only this session's map knew it, so after a restart the
        first load went to the original, ended at once, and was repaired then."""
        from player.audio import mp3_repair
        from player.window.main_load import TrackLoadMixin
        from tests.player.audio.test_mp3_repair import audio
        desk, _rows, _path = self.stand(180_000)
        src = Path(tempfile.mkdtemp(prefix="dp_prior_")) / "misread.mp3"
        src.write_bytes(audio())
        copy = mp3_repair.repaired_copy(src)   # what the earlier session left
        desk._settings = {}
        self.assertEqual(desk._playback.repaired, {})
        url = TrackLoadMixin._source_url(desk, src)
        self.assertEqual(Path(url.toLocalFile()), copy)
        self.assertEqual(desk._playback.repaired[str(src)], copy)

    def test_a_title_without_a_copy_opens_as_itself(self):
        from player.window.main_load import TrackLoadMixin
        from tests.player.audio.test_mp3_repair import audio
        desk, _rows, _path = self.stand(180_000)
        src = Path(tempfile.mkdtemp(prefix="dp_plain_")) / "fine.mp3"
        src.write_bytes(audio())
        desk._settings = {}
        url = TrackLoadMixin._source_url(desk, src)
        self.assertEqual(Path(url.toLocalFile()), src)
        self.assertEqual(desk._playback.repaired, {})

    def test_a_title_that_ends_where_the_library_says_is_no_failure(self):
        desk, _rows, _path = self.stand(180_000)
        self.assertFalse(desk._ended_before_it_began())

    def test_a_title_that_ran_a_while_is_no_failure_whatever_the_length(self):
        desk, _rows, _path = self.stand(77_677_747, since_play=60)
        self.assertFalse(desk._ended_before_it_began())

    def test_a_title_the_library_does_not_know_is_no_failure(self):
        desk, _rows, _path = self.stand(77_677_747)
        desk._library = SimpleNamespace(
            cache=None, lib=SimpleNamespace(entry_for=lambda p: None))
        self.assertFalse(desk._ended_before_it_began())


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
