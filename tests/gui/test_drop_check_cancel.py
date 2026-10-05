#!/usr/bin/env python3
"""A long drop check keeps the window alive and can be cancelled.

Run:  py -m unittest tests.gui.test_drop_check_cancel -v

With 🔇 on, the Check-music drop tab runs a 2-3 s ffmpeg noise probe per
track on the GUI thread. Over 20 tournament lists that was 741 probes: the
window redrew only every fifth track, not at all for a drop of up to 12
tracks, and nothing could stop the pass. The open-deck check already pumps
every track and has a Cancel; the drop tab now does the same.
"""

import unittest
from pathlib import Path
from unittest import mock

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QWidget

import gui.dialogs as gui_dialogs
from gui.dialogs import FileDropCheckPanel
from gui.main_music import MusicCheckMixin
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


class _Host(QWidget, MusicCheckMixin):
    _lib = object()
    _cache = object()

    def _external_entry(self, path):
        return object()

    def _track_issues(self, e, probe_silence=True, in_final=False):
        return []


class MusicDropTicksTest(unittest.TestCase):

    def test_every_track_ticks_the_progress(self):
        host = _Host()
        self.addCleanup(reap_widget, host)
        ticks = []
        tracks = [Path(f"C:/t/{n} (LW 29).mp3") for n in range(7)]
        box = host._dropped_music_results(tracks, lambda d, t: ticks.append(d))
        self.addCleanup(reap_widget, box)
        self.assertEqual(ticks, list(range(1, 8)))


class DropPanelCancelTest(unittest.TestCase):

    def _panel(self, run_fn):
        # Adding a file runs a check at once; the one under test runs on refresh().
        panel = FileDropCheckPanel("info", run_fn=lambda ps, cb: QLabel(""))
        self.addCleanup(reap_widget, panel)
        panel._files.add_paths(["C:/t/a.m3u"])
        panel._run_fn = run_fn
        return panel

    def test_cancel_stops_the_pass(self):
        seen = []

        def run(paths, progress_cb):
            for done in range(1, 41):
                if done == 3:
                    # The click a tick's processEvents delivers.
                    self.assertFalse(panel._cancel_btn.isHidden())
                    panel._cancel_btn.click()
                progress_cb(done, 40)
                seen.append(done)
            return QLabel("all done")

        panel = self._panel(run)
        summaries = []
        panel.resultsReady.connect(summaries.append)
        panel.refresh()
        self.assertEqual(seen, [1, 2])
        self.assertIn("cancelled", panel._results.widget().text())
        self.assertTrue(panel._cancel_btn.isHidden())
        self.assertEqual(summaries[-1], {"files": 1})

    def test_the_next_drop_runs_again(self):
        runs = []

        def run(paths, progress_cb):
            runs.append(1)
            if len(runs) == 1:
                panel._cancel_btn.click()
            progress_cb(1, 40)
            return QLabel("all done")

        panel = self._panel(run)
        panel.refresh()
        panel.refresh()
        self.assertEqual(panel._results.widget().text(), "all done")

    def test_a_short_check_still_pumps_events(self):
        fired = []

        def run(paths, progress_cb):
            QTimer.singleShot(0, lambda: fired.append(1))
            progress_cb(1, 3)
            self.assertEqual(fired, [1])
            return QLabel("ok")

        self._panel(run).refresh()

    def test_a_slow_short_check_shows_cancel(self):
        # 3 tracks, but each probe takes seconds: past 250 ms the Cancel shows.
        clock = iter([0.0, 0.1, 0.4])
        visible = []

        def run(paths, progress_cb):
            progress_cb(1, 3)
            visible.append(not panel._cancel_btn.isHidden())
            progress_cb(2, 3)
            visible.append(not panel._cancel_btn.isHidden())
            return QLabel("ok")

        panel = self._panel(run)
        with mock.patch.object(gui_dialogs.time, "monotonic",
                               side_effect=lambda: next(clock)):
            panel.refresh()
        self.assertEqual(visible, [False, True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
