"""🎛 Pad input details found in review: drag action, release outside, ✕ scope,
tooltip text (#121, #124, #125, #130)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_padinput_"))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from player.widgets import cartwall as gc
from tests.qt_test_support import settle_wall_checks

_app = QApplication.instance() or QApplication(sys.argv)

KEY = (0, 0, 0)


class PadInputTest(unittest.TestCase):

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.resize(600, 400)
        pads = {(0, 0): pc.CartPad(path=r"C:\s\bed.mp3"),
                (0, 1): pc.CartPad(path=r"C:\s\two.mp3")}
        self.w.set_wall(pc.DEFAULT_GRID, [pc.Page(pads=pads)])
        self.w.show()
        self.fired = []
        self.w.padClicked.connect(self.fired.append)
        self.b = self.w._buttons[KEY]
        self.addCleanup(self.w.deleteLater)

    def test_a_release_outside_the_pad_does_not_fire_it(self):
        QTest.mousePress(self.b, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        QTest.mouseRelease(self.b, Qt.MouseButton.LeftButton,
                           pos=QPoint(self.b.width() + 50, 5))
        self.assertEqual(self.fired, [])

    def test_a_release_inside_still_fires(self):
        QTest.mouseClick(self.b, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
        self.assertEqual(self.fired, [KEY])

    def test_the_drag_out_of_a_pad_only_offers_a_copy(self):
        """#121: a Move dropped on Explorer took the sample off the disk."""
        self.w.set_edit(True)
        with mock.patch.object(gc, "QDrag") as drag:
            QTest.mousePress(self.b, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
            QTest.mouseMove(self.b, QPoint(60, 40))
            QTest.mouseMove(self.b, QPoint(90, 60))
        drag.return_value.exec.assert_called_once_with(Qt.DropAction.CopyAction)

    def test_the_x_clears_only_its_own_pad(self):
        """#124: it used to clear the whole selection with no warning."""
        self.w.set_edit(True)
        self.w._selected = {(0, 0, 0), (0, 0, 1)}
        self.w._buttons[KEY]._del_btn.click()
        self.assertIsNone(self.w.pad_at((0, 0, 0)))
        self.assertIsNotNone(self.w.pad_at((0, 0, 1)))

    def test_a_title_that_looks_like_markup_stays_text_in_the_tooltip(self):
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=r"C:\s\a.mp3",
                                                          label="Q&A <b>live</b>")})])
        tip = self.w._buttons[KEY].toolTip()
        self.assertNotIn("<b>live</b>", tip)      # escaped: shown as given
        self.assertIn("&lt;b&gt;live", tip)


class PageAndSelectionTest(unittest.TestCase):

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.resize(600, 400)
        pages = [pc.Page(pads={(0, 1): pc.CartPad(path=r"C:\s\a.mp3")}),
                 pc.Page(pads={(0, 0): pc.CartPad(path=r"C:\s\b.mp3")}),
                 pc.Page(pads={(0, 0): pc.CartPad(path=r"C:\s\c.mp3")})]
        self.w.set_wall(pc.DEFAULT_GRID, pages)
        self.w.show()
        self.addCleanup(self.w.deleteLater)

    def test_removing_a_page_moves_the_voices_of_the_later_ones(self):
        """#126: a voice kept its old page number, so a tap at its new place
        found nothing to stop."""
        moved = []
        self.w.padsMoved.connect(moved.append)
        self.w._page = 1
        with mock.patch.object(gc.QMessageBox, "question",
                               return_value=gc.QMessageBox.StandardButton.Yes):
            self.w._remove_page()
        self.assertEqual(moved, [{(2, 0, 0): (1, 0, 0)}])

    def test_the_selection_follows_the_pads_when_the_grid_is_turned(self):
        """#128: it kept the old cells and pointed at empty ones."""
        self.w.set_edit(True)
        self.w._selected = {(0, 0, 1)}
        self.w.set_portrait(not pc.is_portrait(self.w._grid))
        now = next(k for k, in_ in ((k, self.w.pad_at(k)) for k in
                                    [(0, r, c) for r in range(9) for c in range(9)])
                   if in_ is not None and in_.path.endswith("a.mp3"))
        self.assertEqual(self.w.selection(), {now})


class ButtonStateTest(unittest.TestCase):
    """#129: a button that lost its pad, or was switched to edit mid-scrub,
    kept the old pad's hold, band and scrub."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.resize(600, 400)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path=r"C:\s\a.mp3")})])
        self.w.show()
        self.addCleanup(self.w.deleteLater)
        self.b = self.w._buttons[KEY]

    def test_an_emptied_pad_forgets_hold_band_and_scrub(self):
        self.b._held, self.b._frac, self.b._scrub = True, 0.5, 0.7
        self.b.set_pad(None)
        self.assertEqual((self.b._held, self.b._frac, self.b._scrub), (False, 0.0, None))

    def test_switching_to_edit_mid_scrub_drops_the_scrub(self):
        self.b._scrub = 0.7
        self.b.set_editable(True)
        self.assertIsNone(self.b._scrub)


class FileCheckCacheTest(unittest.TestCase):
    """#127: every page turn stat()ed every pad of every page again, and a
    dead share stalled the GUI thread each time."""

    def setUp(self):
        self.w = gc.CartwallWidget()
        self.w.resize(600, 400)
        self.calls = []
        self.w.set_file_check(lambda p: self.calls.append(p) or True)
        self.w.set_wall(pc.DEFAULT_GRID,
                        [pc.Page(pads={(0, 0): pc.CartPad(path="a.mp3")}),
                         pc.Page(pads={(0, 0): pc.CartPad(path="b.mp3")})])
        settle_wall_checks(self.w)
        self.addCleanup(self.w.deleteLater)

    def test_a_page_turn_does_not_ask_again(self):
        self.calls.clear()
        self.w._rebuild()
        self.w._rebuild()
        self.assertEqual(self.calls, [])

    def test_a_fresh_refresh_asks_again(self):
        self.calls.clear()
        self.w.refresh_missing(fresh=True)
        settle_wall_checks(self.w)
        self.assertEqual(sorted(self.calls), ["a.mp3", "b.mp3"])


class StaleStateTest(PageAndSelectionTest):

    def test_a_pad_gone_while_its_dialog_was_open_is_not_written_back(self):
        """#131: the edit went to coordinates that no longer held that pad."""
        key = (0, 0, 1)
        dlg = mock.Mock()
        dlg.exec.side_effect = lambda: (pc.clear_pad(self.w._pages, 0, (0, 1)),
                                        gc.QDialog.DialogCode.Accepted)[1]
        dlg.pad.return_value = pc.CartPad(path=r"C:\s\z.mp3")
        with mock.patch.object(gc, "CartPadDialog", return_value=dlg):
            self.w._on_edit(key)
        self.assertIsNone(self.w.pad_at(key))

    def test_the_slot_keys_are_cleaned_like_a_file_read(self):
        self.w.apply_keys({}, ["F1", 7, None])
        self.assertEqual(self.w._slot_keys, ("F1",))


if __name__ == "__main__":
    unittest.main()
