"""↩ Pressing play on a title that carries a time marker asks where it starts.

Run:  py -m unittest tests.gui.table.test_play_marked_title -v

Marcel's list, 6.27: "Add a warning if a title has a time marker and I press play,
a confirm dialog to make sure it is wanted like this. Similar to the double-click
warning." A double-click already asked, but only while another title was playing;
the row's ▶ and Space / Enter started a marked title at its marker without a word.
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_play_marked_"))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from gui.decks.running_order import Row, RunningOrder
from gui.table.playlist_table import PlaylistTable
from planner.models import MusicEntry
from shared.columns import _COL_PLAY
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])

_MUSIC = Path(tempfile.mkdtemp(prefix="dp_play_marked_m_"))


def _meta(name: str, h_idx: int) -> Row:
    path = _MUSIC / f"{name}.mp3"
    path.write_bytes(b"x")
    return Row(entry=MusicEntry(path=path, title=name, dance="WW", bpm=29),
               dance="WW", h_idx=h_idx)


class _Win(QWidget):
    running = False

    def __init__(self):
        super().__init__()
        self.cleared = []

    def _clear_resume(self, path):
        self.cleared.append(path)

    def _is_player_running(self) -> bool:
        return self.running

    def _is_player_stopped(self) -> bool:
        return not self.running


class PlayMarkedTitleTest(unittest.TestCase):

    MARKED = _MUSIC / "second.mp3"

    def setUp(self):
        self.win = _Win()
        t = self.t = PlaylistTable()
        t.setParent(self.win)
        t.resize(700, 300)
        t.setRowCount(2)
        t._row_meta = RunningOrder([_meta("first", 0), _meta("second", 1)])
        self.played = []
        t._play_cb = self.played.append
        for row in range(2):
            t._refill_row(row, t._row_meta[row])
        t.set_play_highlight_enabled(True)
        t._resume_marks = {str(self.MARKED): 65_000}
        self.cleared = self.win.cleared
        self.win.show()
        self.addCleanup(reap_widget, self.win)
        self.asked = []
        self.answer = "mark"

        def ask_mark(title, ms, *running):
            self.asked.append((title, ms, *running))
            return self.answer
        t._ask_resume_mark = ask_mark

    def press_play(self, row):
        self.t._on_row_button(row, _COL_PLAY)

    def test_the_marked_title_asks_before_it_starts(self):
        self.press_play(1)
        self.assertEqual(self.asked, [("second", 65_000, False)])
        self.assertEqual(self.played, [self.MARKED])
        self.assertEqual(self.cleared, [])

    def test_from_the_beginning_drops_the_marker_first(self):
        self.answer = "top"
        self.press_play(1)
        self.assertEqual(self.cleared, [self.MARKED])
        self.assertEqual(self.played, [self.MARKED])

    def test_cancel_starts_nothing_and_keeps_the_marker(self):
        self.answer = None
        self.press_play(1)
        self.assertEqual(self.played, [])
        self.assertEqual(self.cleared, [])
        self.assertEqual(self.t._current_play_row, -1)

    def test_a_title_without_a_marker_asks_nothing(self):
        self.press_play(0)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.played, [_MUSIC / "first.mp3"])

    def test_it_says_when_another_title_is_playing(self):
        self.win.running = True
        self.press_play(1)
        self.assertEqual(self.asked, [("second", 65_000, True)])

    def test_the_running_marked_title_is_stopped_without_a_question(self):
        self.press_play(1)
        self.asked.clear()
        self.win.running = True
        self.press_play(1)                              # ■ on the running row
        self.assertEqual(self.asked, [])
        self.assertEqual(self.played[-1], None)

    def test_planning_mode_has_no_marker_to_spend(self):
        self.t.set_play_highlight_enabled(False)
        self.press_play(1)
        self.assertEqual(self.asked, [])
        self.assertEqual(self.played, [self.MARKED])

    def test_space_asks_too(self):
        self.t.selectRow(1)
        QTest.keyClick(self.t, Qt.Key.Key_Space)
        self.assertEqual(self.asked, [("second", 65_000, False)])
        self.assertEqual(self.played, [self.MARKED])

    def test_enter_asks_too_and_cancel_holds(self):
        self.answer = None
        self.t.selectRow(1)
        QTest.keyClick(self.t, Qt.Key.Key_Return)
        self.assertEqual(self.asked, [("second", 65_000, False)])
        self.assertEqual(self.played, [])


class MarkedQuestionWordingTest(unittest.TestCase):
    """The real dialog: with nothing playing it must not talk about a stop."""

    def text_of(self, running):
        t = PlaylistTable()
        self.addCleanup(reap_widget, t)
        seen = {}

        def go():
            box = QApplication.activeModalWidget()
            seen["text"] = box.text()
            box.buttons()[-1].click()
        QTimer.singleShot(0, go)
        t._ask_resume_mark("second", 65_000, running)
        return seen["text"]

    def test_nothing_playing_just_asks_where_it_starts(self):
        text = self.text_of(False)
        self.assertIn("second", text)
        self.assertIn("1:05", text)
        self.assertNotIn("playing", text)

    def test_a_playing_title_is_still_mentioned(self):
        self.assertIn("A title is playing", self.text_of(True))


if __name__ == "__main__":
    unittest.main()
