#!/usr/bin/env python3
"""⚙ Settings opens as one window — no boxes flashing up before it.

Run:  py -m unittest tests.gui.dialogs.test_settings_no_stray_windows -v

Marcel: "if i open settings menu i still getting a lot of overlay dialog
windows before the real is shown". A widget made visible while it has no
parent yet is a top-level window: `btn.setVisible(True)` before
`layout.addWidget(btn)`, or a group box shown before it joins the tab, pops
up on its own for a moment and only disappears once the layout reparents it.
So every Show event during construction must belong to the dialog itself —
and the dialog is not shown at all until `exec()`.
"""

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_windows_"))

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget

from gui.dialogs.settings_dialog import SettingsDialog
from tests.qt_test_support import reap_widget


class _WindowShows(QObject):
    """Every top-level widget that is shown, by class name."""

    def __init__(self):
        super().__init__()
        self.shown = []

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.Show and isinstance(obj, QWidget)
                and obj.isWindow()):
            self.shown.append(type(obj).__name__)
        return False


class SettingsNoStrayWindowsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def build(self, **callbacks):
        spy = _WindowShows()
        self.app.installEventFilter(spy)
        try:
            dlg = SettingsDialog({}, **callbacks)
        finally:
            self.app.removeEventFilter(spy)
        self.addCleanup(reap_widget, dlg)
        return spy.shown

    def test_building_it_with_every_window_offered_shows_nothing(self):
        def noop(*_a):
            return None
        shown = self.build(remote_cb=noop, guests_cb=noop, controller_cb=noop,
                           desk_keys_cb=noop)
        self.assertEqual(shown, [], "these flashed up as windows of their own")

    def test_building_it_with_nothing_offered_shows_nothing(self):
        self.assertEqual(self.build(), [])


if __name__ == "__main__":
    unittest.main()
