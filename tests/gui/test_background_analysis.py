#!/usr/bin/env python3
"""🔬 New titles get their audio analysis by themselves, a while after startup.

Run:  py -m unittest tests.gui.test_background_analysis -v

Titles added since the last run stayed without tempo and timbre until somebody
pressed 🔬, so they were missing from similar-track search with nothing to say
why. Now they are analyzed in the background, and a show always comes first:
never in a player-only setup, never while music plays, stopped as soon as it
starts, and a whole first run (an hour) stays the button's question.
"""

import gc
import os
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_bg_analysis_"))

from PySide6.QtCore import QThread
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QApplication, QMainWindow

from gui import workers
from gui.window import main_analyze as ma
from gui.window.library_service import LibraryService
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget, stub_window_startup

_app = QApplication.instance() or QApplication([])


def _entries(missing, analyzed=0):
    new = [MusicEntry(path=Path(rf"C:\new\{i}.mp3"), title=f"N{i}") for i in range(missing)]
    old = [MusicEntry(path=Path(rf"C:\old\{i}.mp3"), title=f"O{i}", features=object())
           for i in range(analyzed)]
    return new + old


def _running():
    return mock.Mock(spec=workers.BackgroundAnalyzer,
                     **{"isRunning.return_value": True})


class _Host(QMainWindow, ma.AnalysisMixin):
    def __init__(self, entries, mode="both", playing=False):
        super().__init__()
        self._library = LibraryService()
        self._library.lib = SimpleNamespace(entries=entries)
        self._library.cache = mock.Mock()
        self._settings = {"app_mode": mode}
        self._player = mock.Mock(**{"isPlaying.return_value": playing})
        self._analyzer = None
        self._index_analyzer = None
        self.applied = []

    def _apply_analysis_results(self, ok):
        self.applied.append(ok)


class StartTest(unittest.TestCase):

    def start(self, entries, **kw):
        self.host = _Host(entries, **kw)
        self.addCleanup(self.host.deleteLater)
        with mock.patch.object(ma, "BackgroundAnalyzer") as worker_cls:
            self.host._analyze_new_titles()
        return worker_cls

    def test_only_the_new_titles_are_analyzed(self):
        entries = _entries(3, analyzed=5)
        worker_cls = self.start(entries)
        worker_cls.assert_called_once_with(self.host._library.cache, entries[:3], self.host)

    def test_it_starts_and_is_kept(self):
        worker = self.start(_entries(1)).return_value
        worker.start.assert_called_once_with()
        self.assertIs(self.host._analyzer, worker)

    def test_nothing_new_nothing_runs(self):
        self.start(_entries(0, analyzed=5)).assert_not_called()

    def test_as_many_as_the_cap_still_run(self):
        self.start(_entries(ma._BACKGROUND_ANALYSIS_MAX)).assert_called_once()

    def test_a_first_run_stays_the_buttons_question(self):
        self.start(_entries(ma._BACKGROUND_ANALYSIS_MAX + 1)).assert_not_called()

    def test_not_while_music_plays(self):
        self.start(_entries(3), playing=True).assert_not_called()

    def test_not_in_the_player_only_mode(self):
        self.start(_entries(3), mode="player").assert_not_called()

    def test_a_window_without_a_player_still_analyzes(self):
        host = _Host(_entries(1))
        self.addCleanup(host.deleteLater)
        host._player = None
        with mock.patch.object(ma, "BackgroundAnalyzer") as worker_cls:
            host._analyze_new_titles()
        worker_cls.assert_called_once()

    def test_no_library_nothing_runs(self):
        host = _Host([])
        self.addCleanup(host.deleteLater)
        host._library.lib = None
        with mock.patch.object(ma, "BackgroundAnalyzer") as worker_cls:
            host._analyze_new_titles()
        worker_cls.assert_not_called()

    def test_not_next_to_a_run_already_going(self):
        for name in ("_analyzer", "_index_analyzer"):
            with self.subTest(name):
                host = _Host(_entries(1))
                self.addCleanup(host.deleteLater)
                setattr(host, name, _running())
                with mock.patch.object(ma, "BackgroundAnalyzer") as worker_cls:
                    host._analyze_new_titles()
                worker_cls.assert_not_called()

    def test_it_waits_a_while_after_the_library_came_up(self):
        host = _Host([])
        self.addCleanup(host.deleteLater)
        with mock.patch.object(ma.QTimer, "singleShot") as shot:
            host._schedule_background_analysis()
        shot.assert_called_once_with(ma._BACKGROUND_ANALYSIS_DELAY_MS, host,
                                     host._analyze_new_titles)


class _Cache:
    """analyze_entries until someone cancels, or at once."""

    def __init__(self, hold=False):
        self.hold = hold
        self.calls = 0
        self.entered = threading.Event()

    def analyze_entries(self, entries, should_cancel=None, **_kw):
        self.calls += 1
        self.entered.set()
        while self.hold:
            if should_cancel():
                return 0, 0, True
            QThread.msleep(5)
        return len(entries), 0, False


class WorkerTest(unittest.TestCase):

    def test_a_machine_that_cannot_decode_stays_quiet(self):
        cache = _Cache()
        worker = workers.BackgroundAnalyzer(cache, _entries(2))
        ended = []
        worker.done.connect(lambda *a: ended.append(a))
        with mock.patch.object(workers, "probe_decode_backend", return_value="no backend"):
            worker.run()
        self.assertEqual((cache.calls, ended), (0, []))

    def test_a_working_decoder_goes_on_to_the_analysis(self):
        cache = _Cache()
        worker = workers.BackgroundAnalyzer(cache, _entries(2))
        ended = []
        worker.done.connect(lambda *a: ended.append(a))
        with mock.patch.object(workers, "probe_decode_backend", return_value=None):
            worker.run()
        self.assertEqual(ended, [(2, 0)])

    def test_it_runs_behind_the_music(self):
        worker = workers.BackgroundAnalyzer(_Cache(), _entries(1))
        with mock.patch.object(workers, "probe_decode_backend", return_value=None), \
                mock.patch.object(workers, "lower_thread_priority") as lower:
            worker.run()
        lower.assert_called_once_with()

    def test_the_decode_probe_leaves_the_window_alone(self):
        seen = []
        worker = workers.BackgroundAnalyzer(_Cache(), _entries(1))
        with mock.patch.object(workers, "probe_decode_backend",
                               side_effect=lambda _p: seen.append(QThread.currentThread())):
            worker.start()
            self.assertTrue(worker.wait(5000))
        self.assertEqual(len(seen), 1)
        self.assertIsNot(seen[0], _app.thread())


class FinishTest(unittest.TestCase):

    def host_with_worker(self, cache):
        host = _Host(_entries(2))
        self.addCleanup(host.deleteLater)
        host._library.cache = cache
        patcher = mock.patch.object(workers, "probe_decode_backend", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        host._analyze_new_titles()
        self.assertTrue(cache.entered.wait(5))
        return host

    def finish(self, host):
        self.assertTrue(host._analyzer.wait(5000))
        for _ in range(20):
            _app.processEvents()

    def test_a_machine_that_cannot_decode_does_not_leave_the_bar_up(self):
        """The worker ends without done / cancelled / error when the decode
        probe fails, and the bar was only hidden by those three."""
        host = _Host(_entries(2))
        self.addCleanup(host.deleteLater)
        host._library.cache = _Cache()
        with mock.patch.object(workers, "probe_decode_backend",
                               return_value="no backend"):
            host._analyze_new_titles()
            self.assertFalse(host._library.background_bar.isHidden())
            self.assertTrue(host._analyzer.wait(5000))
            for _ in range(20):
                _app.processEvents()
        self.assertTrue(host._library.background_bar.isHidden())

    def test_the_results_reach_the_library(self):
        host = self.host_with_worker(_Cache())
        self.finish(host)
        self.assertEqual(host.applied, [2])

    def test_stopping_ends_the_run_and_applies_nothing(self):
        host = self.host_with_worker(_Cache(hold=True))
        host._stop_background_analysis()
        self.finish(host)
        self.assertEqual(host.applied, [])

    def test_a_stopped_run_may_lose_its_place_to_the_next(self):
        """🔬 puts its own run on `_analyzer` while this title still ends;
        the window is the thread's parent and keeps it alive."""
        host = self.host_with_worker(_Cache(hold=True))
        host._stop_background_analysis()
        host._analyzer = None
        gc.collect()
        self.assertTrue(host.findChild(workers.BackgroundAnalyzer).wait(5000))

    def test_a_run_with_nothing_to_show_applies_nothing(self):
        host = _Host(_entries(1))
        self.addCleanup(host.deleteLater)
        host._on_background_analysis_done(0, 1)
        self.assertEqual(host.applied, [])

    def test_stopping_with_nothing_running_is_fine(self):
        host = _Host([])
        self.addCleanup(host.deleteLater)
        host._stop_background_analysis()


class WindowTest(unittest.TestCase):
    """The hooks of the real window: whatever needs the machine comes first."""

    @classmethod
    def setUpClass(cls):
        dancesport_gui = stub_window_startup(cls)
        cls.win = dancesport_gui.MainWindow()
        cls.addClassCleanup(reap_widget, cls.win)

    def setUp(self):
        self.worker = self.win._analyzer = _running()
        self.addCleanup(setattr, self.win, "_analyzer", None)

    def press_analyze(self, answer):
        library = self.win._library
        self.addCleanup(setattr, library, "lib", library.lib)
        self.addCleanup(setattr, library, "cache", library.cache)
        library.lib = SimpleNamespace(entries=_entries(1))
        library.cache = mock.Mock()
        with mock.patch.object(self.win, "_library_still_loading", return_value=False), \
                mock.patch.object(self.win, "_librosa_unavailable", return_value=""), \
                mock.patch.object(ma.QMessageBox, "question", return_value=answer), \
                mock.patch.object(ma, "AudioAnalyzer"), \
                mock.patch.object(self.win, "_run_library_pass"):
            self.win._analyze_audio()

    def test_the_music_starting_stops_it(self):
        self.win._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        self.worker.cancel.assert_called_once()

    def test_asking_for_a_title_stops_it_before_the_music_plays(self):
        # Not at the PlayingState that follows: the load of the title comes first.
        order = []
        self.worker.cancel.side_effect = lambda: order.append("cancel")
        with mock.patch.object(self.win, "_player") as player,                 mock.patch.object(self.win, "_sync_big_player_limit"):
            player.stop.side_effect = lambda: order.append("stop")
            self.win._load_track(Path("D:/Musik/a.mp3"), True)
        self.worker.cancel.assert_called_once()
        self.assertEqual(order[:1], ["cancel"])

    def test_cueing_a_title_or_stopping_leaves_it_running(self):
        with mock.patch.object(self.win, "_player"),                 mock.patch.object(self.win, "_sync_big_player_limit"):
            self.win._load_track(Path("D:/Musik/a.mp3"), False)
            self.win._load_track(None, True)
        self.worker.cancel.assert_not_called()

    def test_the_music_stopping_leaves_it_running(self):
        self.win._on_playback_state(QMediaPlayer.PlaybackState.StoppedState)
        self.worker.cancel.assert_not_called()

    def test_the_music_leaves_a_run_of_the_button_alone(self):
        manual = self.win._analyzer = mock.Mock(
            spec=workers.AudioAnalyzer, **{"isRunning.return_value": True})
        self.win._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
        manual.cancel.assert_not_called()

    def test_the_analyze_button_takes_over(self):
        self.press_analyze(ma.QMessageBox.StandardButton.Yes)
        self.worker.cancel.assert_called_once()

    def test_answering_no_to_the_button_changes_nothing(self):
        self.press_analyze(ma.QMessageBox.StandardButton.No)
        self.worker.cancel.assert_not_called()


class ProgressBarTest(unittest.TestCase):
    """The run shows in the status bar, as the library scan does: a count, the
    time left and a bar, with nothing modal in a show's way."""

    def start(self):
        self.host = _Host(_entries(3))
        self.addCleanup(self.host.deleteLater)
        with mock.patch.object(ma, "BackgroundAnalyzer") as worker_cls:
            worker_cls.return_value = _running()
            self.host._analyze_new_titles()
        self.worker = worker_cls.return_value
        self.bar = self.host._library.background_bar

    def emit(self, signal_name, *args):
        getattr(self.worker, signal_name).connect.call_args.args[0](*args)

    def test_the_bar_is_up_from_the_start_with_the_count_of_titles(self):
        self.start()
        self.assertFalse(self.bar.isHidden())
        self.assertIn("3", self.bar.label.text())

    def test_progress_shows_count_time_left_and_the_bar(self):
        self.start()
        self.emit("progress", 1, 3, 0, "a.m4a", 13.0)
        self.assertIn("1/3", self.bar.label.text())
        self.assertIn("13s", self.bar.label.text())
        self.assertEqual((self.bar.progress.value(), self.bar.progress.maximum()), (1, 3))

    def test_errors_are_counted(self):
        self.start()
        self.emit("progress", 2, 3, 1, "a.m4a", 4.0)
        self.assertIn("1", self.bar.label.text().split("2/3")[1])

    def test_done_cancelled_and_error_take_it_down(self):
        for signal_name, args in (("done", (3, 0)), ("cancelled", (1,)), ("error", ("boom",))):
            with self.subTest(signal_name):
                self.start()
                self.emit(signal_name, *args)
                self.assertTrue(self.bar.isHidden())

    def test_the_stop_button_cancels_the_run_and_says_so(self):
        self.start()
        self.bar.stop_btn.click()
        self.worker.cancel.assert_called_once_with()
        self.assertFalse(self.bar.stop_btn.isEnabled())    # asked once is enough

    def test_a_new_run_gets_its_button_back(self):
        self.start()
        self.bar.stop_btn.click()
        self.bar.start(5)
        self.assertTrue(self.bar.stop_btn.isEnabled())

    def test_it_sits_in_the_status_bar(self):
        self.start()
        self.assertIs(self.bar.parentWidget(), self.host.statusBar())


if __name__ == "__main__":
    unittest.main(verbosity=2)
