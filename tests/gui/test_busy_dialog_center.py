"""A wait dialog comes up centred on its window, at its real size.

Run:  py -m unittest tests.gui.test_busy_dialog_center -v

Filmed on screen for Marcel's "the dialog that appears is strange": the
"📁 Reading the dropped folder…" dialog stood with its top-left corner near
the middle of the window. `_center` measured it before its layout had ever
run, while it still had Qt's default size, and the dialog shrank to its
real size afterwards around the wrong point.
"""
import os
import sys
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_busy_center_"))

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from gui.common import BusyDialog  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


class BusyCenterTest(unittest.TestCase):

    def test_it_stands_in_the_middle_of_its_window(self):
        win = QWidget()
        self.addCleanup(reap_widget, win)
        win.setGeometry(100, 100, 1200, 800)
        win.show()
        dlg = BusyDialog(win, message="📁 Reading the dropped folder…")
        dlg.show_after(0)
        for _ in range(3):
            _app.processEvents()
        self.assertTrue(dlg.isVisible())
        mid, want = dlg.geometry().center(), win.geometry().center()
        self.assertLessEqual(abs(mid.x() - want.x()), 2, (mid, want))
        self.assertLessEqual(abs(mid.y() - want.y()), 2, (mid, want))
        dlg.finish()


if __name__ == "__main__":
    unittest.main(verbosity=2)
