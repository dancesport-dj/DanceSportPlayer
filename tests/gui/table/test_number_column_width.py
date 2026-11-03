"""The Nb. column: as wide as its counter, unless the user says otherwise.

Run:  py -m unittest tests.gui.table.test_number_column_width -v

Marcel's list, 6.8: "Allow resizing the numbers column. Default stays auto-sized
to the counter width (like 99 or 199), but the user can make it narrower or
wider." A vertical header has no handle of its own, so a strip on its right edge
is one. The width goes with the other columns' widths, per kind of list.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_nb_width_"))

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from gui.dialogs import _add_deck_column
from gui.table.playlist_table import PlaylistTable
from gui.window import main_libpane
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])


def _e(n):
    return MusicEntry(path=Path(rf"C:\music\{n}.mp3"), title=str(n), dance="LW",
                      duration=150)


def _send(widget, kind, x, buttons=Qt.MouseButton.LeftButton):
    """Mouse event at global `x`: a real drag leaves the strip behind at once."""
    QApplication.sendEvent(widget, QMouseEvent(
        kind, QPointF(1, 1), QPointF(x, 10), Qt.MouseButton.LeftButton, buttons,
        Qt.KeyboardModifier.NoModifier))


class _Base(unittest.TestCase):

    def numbered(self, titles=3):
        t = PlaylistTable()
        t.resize(700, 400)
        self.addCleanup(reap_widget, t)
        t.load_wishlist([_e(n) for n in range(titles)], mock.Mock(), None)
        t.set_numbered(True)
        return t

    @staticmethod
    def drag(t, by):
        grip = t._nb_grip
        _send(grip, QEvent.Type.MouseButtonPress, 100)
        _send(grip, QEvent.Type.MouseMove, 100 + by)
        _send(grip, QEvent.Type.MouseButtonRelease, 100 + by, Qt.MouseButton.NoButton)

    @staticmethod
    def gutter(t):
        return t.verticalHeader().width()

    @staticmethod
    def text_width(t, text):
        return t._nb_label.fontMetrics().horizontalAdvance(text)


class AutomaticWidthTest(_Base):

    def test_it_fits_a_three_digit_counter(self):
        t = self.numbered(150)
        self.assertGreaterEqual(self.gutter(t), self.text_width(t, "199") + 7)

    def test_a_short_list_needs_less_than_a_long_one(self):
        self.assertLessEqual(self.gutter(self.numbered(9)),
                             self.gutter(self.numbered(150)))

    def test_four_digits_get_their_room(self):
        """It used to be 999 wide whatever the list held."""
        t = self.numbered(1200)
        self.assertGreaterEqual(self.gutter(t), self.text_width(t, "1200") + 7)

    def test_it_follows_the_list(self):
        t = self.numbered(3)
        before = self.gutter(t)
        t.load_wishlist([_e(n) for n in range(1200)], mock.Mock(), None)
        _app.processEvents()
        self.assertGreater(self.gutter(t), before)


class HandleTest(_Base):

    def test_it_sits_on_the_right_edge(self):
        t = self.numbered()
        t.show()
        self.addCleanup(t.hide)
        _app.processEvents()
        edge = t.frameWidth() + self.gutter(t) - 2
        self.assertIs(t.childAt(edge, 60), t._nb_grip)
        self.assertIs(t.childAt(edge, 5), t._nb_grip)
        self.assertEqual(t._nb_grip.cursor().shape(), Qt.CursorShape.SplitHCursor)

    def test_no_numbers_no_handle(self):
        t = self.numbered()
        self.assertTrue(t._nb_grip.isVisibleTo(t))
        t.set_numbered(False)
        self.assertFalse(t._nb_grip.isVisibleTo(t))

    def test_dragging_makes_it_wider_or_narrower(self):
        t = self.numbered()
        start = self.gutter(t)
        self.drag(t, 30)
        self.assertEqual(self.gutter(t), start + 30)
        self.drag(t, -12)
        self.assertEqual(self.gutter(t), start + 18)

    def test_the_label_goes_along(self):
        t = self.numbered()
        self.drag(t, 30)
        self.assertEqual(t._nb_label.width(), self.gutter(t))

    def test_it_stays_within_reach(self):
        t = self.numbered()
        self.drag(t, -500)
        self.assertGreater(self.gutter(t), 10)
        self.drag(t, 2000)
        self.assertLess(self.gutter(t), 200)

    def test_a_list_growing_leaves_a_chosen_width_alone(self):
        t = self.numbered(3)
        self.drag(t, 40)
        chosen = self.gutter(t)
        t.load_wishlist([_e(n) for n in range(1200)], mock.Mock(), None)
        _app.processEvents()
        self.assertEqual(self.gutter(t), chosen)

    def test_a_double_click_hands_it_back_to_the_counter(self):
        t = self.numbered()
        start = self.gutter(t)
        self.drag(t, 40)
        _send(t._nb_grip, QEvent.Type.MouseButtonDblClick, 100)
        self.assertEqual(self.gutter(t), start)

    def test_a_grabbed_column_keeps_the_mouse_offset(self):
        """No jump on the press: the width moves by what the mouse moved."""
        t = self.numbered()
        start = self.gutter(t)
        _send(t._nb_grip, QEvent.Type.MouseButtonPress, 700)
        _send(t._nb_grip, QEvent.Type.MouseMove, 700)
        self.assertEqual(self.gutter(t), start)


class SavedWidthTest(_Base):

    def test_the_automatic_width_is_not_saved(self):
        """A saved number would stop it following the list."""
        self.assertTrue(all(c >= 0 for c in self.numbered().column_widths()))

    def test_a_drag_is_reported_once_it_ends(self):
        t = self.numbered()
        seen = mock.Mock()
        t.set_widths_callback(seen)
        grip = t._nb_grip
        _send(grip, QEvent.Type.MouseButtonPress, 100)
        _send(grip, QEvent.Type.MouseMove, 130)
        seen.assert_not_called()
        _send(grip, QEvent.Type.MouseButtonRelease, 130, Qt.MouseButton.NoButton)
        seen.assert_called_once()
        self.assertIn(self.gutter(t), seen.call_args.args[1].values())

    def test_a_double_click_is_reported_too(self):
        t = self.numbered()
        self.drag(t, 30)
        seen = mock.Mock()
        t.set_widths_callback(seen)
        _send(t._nb_grip, QEvent.Type.MouseButtonDblClick, 100)
        self.assertTrue(all(c >= 0 for c in seen.call_args.args[1]))

    def test_it_survives_the_settings_file(self):
        t = self.numbered()
        self.drag(t, 30)
        wanted = self.gutter(t)
        other = self.numbered()
        other.set_column_widths(json.loads(json.dumps(t.column_widths())))
        self.assertEqual(self.gutter(other), wanted)

    def test_the_other_lists_of_the_kind_follow(self):
        a, b = self.numbered(), self.numbered()
        a.list_kind = b.list_kind = "playlist"
        win = SimpleNamespace(_settings={}, _deckset=SimpleNamespace(all_tables=[a, b]))
        changed = main_libpane.LibraryPaneMixin
        with mock.patch.object(main_libpane, "save_settings"):
            start = self.gutter(b)
            self.drag(a, 30)
            changed._on_column_widths_changed(win, "playlist", a.column_widths())
            self.assertEqual(self.gutter(b), start + 30)
            _send(a._nb_grip, QEvent.Type.MouseButtonDblClick, 100)
            changed._on_column_widths_changed(win, "playlist", a.column_widths())
            self.assertEqual(self.gutter(b), start)

    def test_a_new_column_does_not_move_it(self):
        t = self.numbered()
        self.drag(t, 30)
        widths = {str(c): w for c, w in t.column_widths().items()}
        settings = {"column_widths": {"playlist": widths}}
        _add_deck_column(settings, 3)
        self.assertEqual(settings["column_widths"]["playlist"]["-1"], self.gutter(t))


if __name__ == "__main__":
    unittest.main()
