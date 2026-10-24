#!/usr/bin/env python3
"""After a crash the desk offers the title that was on air, from its start.

Run:  py -m unittest tests.gui.window.test_crash_resume -v

The autosave brings the decks back after a crash, but not what was playing:
the operator had to find the row again, with the couples standing. Once a
title plays in Playing mode, the tick notes its deck and row on disk — once a
title, off the GUI thread (tests/player/test_on_air_note.py); every stop and a
clean quit take the note away again. A note found at the next start means the
last run did not end — the desk asks whether to cue that title again, from its
start.

▶ The titles the evening had played come along in the same question and
grey out again; with no title on air they are asked about on their own.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_crash_resume_"))

from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtWidgets import QMessageBox

from dancesport_planner import MusicLibrary
from planner.models import MusicEntry
from planner.playing import play_session
from player.audio.on_air_note import NOTE
from player.window.main_resume import EVENING
from shared.stores import ON_AIR
from tests.qt_test_support import reap_widget, stub_window_startup

SONGS = [MusicEntry(path=Path(rf"C:\music\tanzcds\LW{i}.mp3"),
                    title=f"LW {i}", dance="LW", duration=180)
         for i in (1, 2, 3)]


class CrashResumeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_crash_resume_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def setUp(self):
        NOTE.flush()
        ON_AIR.remove()
        self.addCleanup(ON_AIR.remove)
        self.addCleanup(NOTE.flush)
        EVENING.flush()
        play_session.clear()
        self.addCleanup(play_session.clear)
        self.addCleanup(EVENING.flush)
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win._library.lib = MusicLibrary()
        self.deck = self.win._deckset.tableB
        self.deck.load_player_list(SONGS, "🏁 Order", lambda *a: None, None)
        self.index = self.win._deckset.all_tables.index(self.deck)
        # Table rows, not song numbers: the deck sets rows between its titles.
        self.rows = [r for r, _ in self.deck._row_meta.numbered()]

    def play_on_air(self, song=1, pos=95_000):
        """Title `song` of deck B playing in Playing mode at `pos`, one tick."""
        win = self.win
        win._set_play_mode(True)
        self.deck.cue_row(self.rows[song], False)
        win._playback.path = SONGS[song].path
        player = mock.Mock()
        player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
        player.position.return_value = pos
        player.duration.return_value = 180_000
        player.playbackRate.return_value = 1.0
        win._player = player
        # Stopped again before the window goes, or its close asks to quit.
        self.addCleanup(setattr, player.playbackState, "return_value",
                        QMediaPlayer.PlaybackState.StoppedState)
        self.tick()

    def tick(self):
        with mock.patch.object(self.win, "_log_play"), \
                mock.patch.object(self.win, "_maybe_skip_silence", return_value=False):
            self.win._on_play_tick()

    def offer(self):
        """Run the start's offer; the box it opened, or None."""
        self.win._offer_crash_resume()
        boxes = [b for b in self.win.findChildren(QMessageBox) if b.isVisible()]
        return boxes[0] if boxes else None

    def test_a_playing_title_leaves_a_note(self):
        self.play_on_air()
        self.assertTrue(NOTE.flush())
        self.assertEqual(ON_AIR.read(), {"table": self.index, "row": self.rows[1],
                                         "path": str(SONGS[1].path)})

    def test_the_note_is_written_once_a_title(self):
        with mock.patch.object(NOTE, "write") as write:
            self.play_on_air()
            self.win._player.position.return_value = 96_000
            self.tick()
        write.assert_called_once()

    def test_a_stop_takes_the_note_away(self):
        self.play_on_air()
        self.win._stop_play_timer()
        self.assertTrue(NOTE.flush())
        self.assertFalse(ON_AIR.exists())

    def test_no_note_no_question(self):
        self.assertIsNone(self.offer())

    def test_yes_cues_the_title_from_its_start(self):
        ON_AIR.write({"table": self.index, "row": self.rows[2],
                      "path": str(SONGS[2].path)})
        box = self.offer()
        self.assertIsNotNone(box)
        self.assertIn("LW3", box.text())
        with mock.patch.object(self.win, "_load_track") as load:
            box.button(QMessageBox.StandardButton.Yes).click()
        load.assert_called_once_with(SONGS[2].path, False)
        self.assertIsNone(self.win._resume_seek_ms)
        self.assertEqual(self.deck._current_play_row, self.rows[2])
        self.assertTrue(self.win._is_playing_mode())
        self.assertFalse(ON_AIR.exists())

    def test_no_leaves_the_desk_as_it_is(self):
        ON_AIR.write({"table": self.index, "row": self.rows[2],
                      "path": str(SONGS[2].path)})
        box = self.offer()
        with mock.patch.object(self.win, "_load_track") as load:
            box.button(QMessageBox.StandardButton.No).click()
        load.assert_not_called()
        self.assertFalse(ON_AIR.exists())

    def test_a_row_that_moved_is_found_by_its_title(self):
        ON_AIR.write({"table": self.index, "row": 0,
                      "path": str(SONGS[2].path)})
        box = self.offer()
        with mock.patch.object(self.win, "_load_track"):
            box.button(QMessageBox.StandardButton.Yes).click()
        self.assertEqual(self.deck._current_play_row, self.rows[2])

    def test_a_title_no_longer_on_its_deck_is_not_offered(self):
        ON_AIR.write({"table": self.index, "row": 1,
                      "path": r"C:\music\gone.mp3"})
        self.assertIsNone(self.offer())
        self.assertFalse(ON_AIR.exists())


    # ----- ▶ the evening's played titles ---------------------------------------

    def evening(self, *songs):
        play_session.STORE.write(play_session.to_json(play_session.Session(
            datetime.now() - timedelta(minutes=4), [str(SONGS[i].path) for i in songs])))

    def test_a_greyed_title_writes_the_evening_down(self):
        self.play_on_air()   # 1:35 in: heard, greyed
        self.assertTrue(EVENING.flush())
        s = play_session.load(datetime.now())
        assert s is not None
        self.assertEqual(s.played, [str(SONGS[1].path)])

    def test_after_a_crash_one_question_asks_for_both(self):
        self.evening(0, 1)
        ON_AIR.write({"table": self.index, "row": self.rows[2],
                      "path": str(SONGS[2].path)})
        box = self.offer()
        assert box is not None
        self.assertEqual(len([b for b in self.win.findChildren(QMessageBox)
                              if b.isVisible()]), 1)
        self.assertIn("LW3", box.text())
        self.assertIn("2", box.text())
        with mock.patch.object(self.win, "_load_track") as load:
            box.button(QMessageBox.StandardButton.Yes).click()
        load.assert_called_once_with(SONGS[2].path, False)
        self.assertEqual(self.deck._played_paths, {str(SONGS[0].path), str(SONGS[1].path)})
        self.assertEqual(self.deck._current_play_row, self.rows[2])

    def test_no_after_a_crash_forgets_the_evening_too(self):
        self.evening(0)
        ON_AIR.write({"table": self.index, "row": self.rows[2],
                      "path": str(SONGS[2].path)})
        box = self.offer()
        assert box is not None
        with mock.patch.object(self.win, "_load_track"):
            box.button(QMessageBox.StandardButton.No).click()
        self.assertEqual(self.deck._played_paths, set())
        self.assertIsNone(play_session.load(datetime.now()))

    def test_with_no_title_on_air_the_evening_is_asked_alone(self):
        """A restart, or a crash between two titles: no crash note."""
        self.evening(0)
        box = self.offer()
        assert box is not None
        self.assertNotIn("LW", box.text())
        pick = next(b for b in box.buttons()
                    if box.buttonRole(b) == QMessageBox.ButtonRole.AcceptRole)
        with mock.patch.object(self.win, "_load_track") as load:
            pick.click()
        load.assert_not_called()   # nothing cued, nothing started
        self.assertEqual(self.deck._played_paths, {str(SONGS[0].path)})
        self.assertTrue(self.win._is_playing_mode())


if __name__ == "__main__":
    unittest.main(verbosity=2)
