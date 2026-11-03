#!/usr/bin/env python3
"""📥 A venue pack is dropped onto the program window; there is no toolbar button.

Run:  py -m unittest tests.gui.test_venue_pack_drop -v

The pack used to have a toolbar button. Now a .dpvenue file dropped anywhere on
the window starts the import, and the table menu offers it below Import M3U.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_venue_drop_"))

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import QApplication

from planner.event import venue_pack
from tests.qt_test_support import reap_widget, stub_window_startup


def _mime(*names):
    m = QMimeData()
    m.setUrls([QUrl.fromLocalFile(n) for n in names])
    return m


class VenuePackDropTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win.show()
        self.app.processEvents()

    def drop(self, mime):
        pos = QPointF(10, 10)
        enter = QDragEnterEvent(QPoint(10, 10), Qt.DropAction.CopyAction, mime,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.win.dragEnterEvent(enter)
        ev = QDropEvent(pos, Qt.DropAction.CopyAction, mime,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        self.win.dropEvent(ev)
        return enter.isAccepted(), ev.isAccepted()

    def test_the_toolbar_has_no_import_button(self):
        texts = [b.property("fullText") for b in self.win._toolbar_btns]
        self.assertNotIn("📥  Import venue pack", texts)

    def test_a_dropped_pack_starts_the_import(self):
        path = str(Path("x") / ("a" + venue_pack.SUFFIX))
        with mock.patch.object(self.win, "_import_venue_pack") as imp:
            accepted = self.drop(_mime(path))
        imp.assert_called_once_with(Path(path))
        self.assertEqual(accepted, (True, True))

    def test_other_files_are_not_taken(self):
        with mock.patch.object(self.win, "_import_venue_pack") as imp:
            accepted = self.drop(_mime("song.mp3"))
        imp.assert_not_called()
        self.assertEqual(accepted, (False, False))


if __name__ == "__main__":
    unittest.main()
