"""The 📚 library pane's class filter takes several classes at once.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_library_class_multi -v

Marcel: "library selector for dance class: make multi selection possible".
A click on a class ticks it and leaves the list open for the next one; a
title passes when it suits ANY ticked class. "All classes" clears the ticks.

Marcel: "Titel ohne Klassen-Tag erscheinen weiterhin immer: nur zeigen wenn
alle angewählt" - a title without a class tag shows only under All classes
or with every class ticked. Social dances have no classes and stay.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_classmulti_"))

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyledItemDelegate

from gui.library_browser import LibraryBrowser
from planner.models import MusicEntry
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication(sys.argv)

_COL_TITLE = 3


def _entry(title, classes_ok=None):
    return MusicEntry(path=Path(rf"C:\music\tanzcds\{title}.mp3"), title=title,
                      dance="LW", bpm=29, classes_ok=classes_ok)


_D_ONLY = _entry("d only", ["D"])
_C_ONLY = _entry("c only", ["C"])
_S_ONLY = _entry("s only", ["S"])
_UNTAGGED = _entry("untagged")
_SOCIAL = MusicEntry(path=Path(r"C:\music\social\salsa.mp3"), title="salsa",
                     dance=None, bpm=50)


class ClassMultiSelectTest(unittest.TestCase):

    def setUp(self):
        self.pane = LibraryBrowser()
        self.addCleanup(reap_widget, self.pane)
        self.pane.set_entries([_D_ONLY, _C_ONLY, _S_ONLY, _UNTAGGED, _SOCIAL])
        self.combo = self.pane._class_combo

    def _shown(self) -> set:
        t = self.pane._table
        return {t.item(r, _COL_TITLE).text() for r in range(t.rowCount())}

    def _click_item(self, data):
        """Release the mouse on an entry of the open list, as a click does."""
        view = self.combo.view()
        rect = view.visualRect(self.combo.model().index(self.combo.findData(data), 0))
        pos = QPointF(rect.center())
        for kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            ev = QMouseEvent(kind, pos, view.viewport().mapToGlobal(pos),
                             Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier)
            QApplication.sendEvent(view.viewport(), ev)

    def test_nothing_ticked_shows_every_class(self):
        self.assertEqual(self.combo.classes(), [])
        self.assertEqual(self._shown(),
                         {"d only", "c only", "s only", "untagged", "salsa"})

    def test_two_ticked_classes_show_either(self):
        self.combo.set_classes(["D", "C"])
        self.assertEqual(self._shown(), {"d only", "c only", "salsa"})

    def test_every_class_ticked_shows_the_untagged_too(self):
        self.combo.set_classes(["D", "C", "B", "A", "S"])
        self.assertEqual(self._shown(),
                         {"d only", "c only", "s only", "untagged", "salsa"})

    def test_a_click_ticks_and_keeps_the_list_open(self):
        self.pane.show()
        self.combo.showPopup()
        self._click_item("D")
        self._click_item("C")
        self.assertTrue(self.combo.view().isVisible())
        self.assertEqual(self.combo.classes(), ["D", "C"])
        self.assertEqual(self._shown(), {"d only", "c only", "salsa"})
        self._click_item("D")
        self.assertEqual(self.combo.classes(), ["C"])
        self.assertEqual(self._shown(), {"c only", "salsa"})
        # Unticking the last class is mid-choice: the list stays open.
        self._click_item("C")
        self.assertEqual(self.combo.classes(), [])
        self.assertTrue(self.combo.view().isVisible())

    def _release_on_item(self, data):
        """Only the release, as when the click that opened the list ends on it."""
        view = self.combo.view()
        rect = view.visualRect(self.combo.model().index(self.combo.findData(data), 0))
        pos = QPointF(rect.center())
        QApplication.sendEvent(view.viewport(), QMouseEvent(
            QEvent.Type.MouseButtonRelease, pos, view.viewport().mapToGlobal(pos),
            Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier))

    def test_the_opening_click_leaves_the_list_open(self):
        # Marcel: the list shut again on the first click. Fusion lays the list
        # over the box with "All classes" under the mouse, so the release of
        # the click that opened it landed there and cleared and closed it.
        self.pane.show()
        self.combo.set_classes(["D", "S"])
        QTest.mousePress(self.combo, Qt.MouseButton.LeftButton)
        self.assertTrue(self.combo.view().isVisible())
        self._release_on_item("")
        self.assertTrue(self.combo.view().isVisible())
        self.assertEqual(self.combo.classes(), ["D", "S"])
        self._click_item("C")
        self.assertEqual(self.combo.classes(), ["D", "C", "S"])

    def test_the_ticks_are_small_item_view_boxes(self):
        # Marcel: the check boxes were big. The combo's own menu delegate
        # draws them as ~20 px menu ticks; an item-view delegate draws the
        # style's indicator, 14 px in Fusion, the size of the text.
        view = self.combo.view()
        self.assertIsInstance(view.itemDelegate(), QStyledItemDelegate)
        # ...but the rows stay as tall as the menu's were, easy to hit.
        self.assertGreaterEqual(view.sizeHintForRow(1), view.fontMetrics().height() + 8)

    def test_all_classes_clears_the_ticks(self):
        self.pane.show()
        self.combo.set_classes(["D", "S"])
        self.combo.showPopup()
        self._click_item("")
        self.assertEqual(self.combo.classes(), [])
        self.assertEqual(len(self._shown()), 5)

    def test_ticking_every_class_switches_to_all_classes(self):
        # Marcel: "for the class filter if all checked show All classes in
        # the label box and switch to the entry".
        self.pane.show()
        self.combo.showPopup()
        for cls in ("D", "C", "B", "A", "S"):
            self._click_item(cls)
        self.assertEqual(self.combo.classes(), [])
        self.assertEqual(self.combo.summary(), "All classes")
        # Marcel: the open list flickered as its ticks vanished; close it.
        self.assertFalse(self.combo.view().isVisible())
        self.assertEqual(len(self._shown()), 5)
        self.combo.set_classes(["D", "C", "B", "A", "S"])
        self.assertEqual(self.combo.classes(), [])

    def test_the_box_names_what_is_ticked(self):
        self.assertEqual(self.combo.summary(), "All classes")
        self.combo.set_classes(["C", "D"])
        self.assertEqual(self.combo.summary(), "Class D + C")

    def test_a_filter_jump_sets_one_class(self):
        self.combo.set_classes(["D", "C"])
        self.pane.focus_filter(cls="S")
        self.assertEqual(self.combo.classes(), ["S"])
        self.assertEqual(self._shown(), {"s only", "salsa"})
        self.pane.focus_filter(dance="LW")
        self.assertEqual(self.combo.classes(), [])


if __name__ == "__main__":
    unittest.main()
