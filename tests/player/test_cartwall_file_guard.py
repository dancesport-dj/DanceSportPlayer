#!/usr/bin/env python3
"""Tests for leaving a cartwall.json this build cannot read alone.

Run:  py -m unittest tests.player.test_cartwall_file_guard -v

A newer build's wall starts this one empty, and the file is to stay untouched
until the operator edits the wall — that edit is them starting over. But the
startup dock restore turns the wall to fit its edge, the turn is a change, and
the change was saved: the newer wall was gone before anyone touched a pad.
"""
import json
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_cartguard_"))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

from shared import stores  # noqa: E402
from planner import cartwall as pc  # noqa: E402
from player.main_cartwall import CartwallMixin  # noqa: E402
from tests.qt_test_support import reap_widget  # noqa: E402

NEWER = {"version": pc.CARTWALL_VERSION + 1, "pages": [{"name": "from the future"}]}


class _Host(CartwallMixin, QMainWindow):
    """Just the wall, its dock and its file."""

    def __init__(self):
        QMainWindow.__init__(self)
        self._player = None
        self._cart_voices = None
        self._cartwall_shown = True
        self._build_cartwall()


class NewerWallFileTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        stores.CARTWALL.path.write_text(json.dumps(NEWER), encoding="utf-8")
        self.addCleanup(stores.CARTWALL.remove)
        self.host = _Host()
        self.addCleanup(reap_widget, self.host)

    def _on_disk(self):
        return json.loads(stores.CARTWALL.path.read_text(encoding="utf-8"))

    def test_the_startup_dock_restore_does_not_write_over_it(self):
        for area in (Qt.DockWidgetArea.TopDockWidgetArea,
                     Qt.DockWidgetArea.LeftDockWidgetArea):
            self.host._on_cart_dock_moved(area)
        self.assertEqual(self._on_disk(), NEWER)

    def test_saving_everything_does_not_write_over_it_either(self):
        """📌 saves the whole session — the empty stand-in wall is not in it."""
        self.host._save_cartwall(edit=False)
        self.assertEqual(self._on_disk(), NEWER)

    def test_an_edit_of_the_wall_is_starting_over(self):
        self.host._cartwall.changed.emit()
        self.assertEqual(self._on_disk()["version"], pc.CARTWALL_VERSION)


if __name__ == "__main__":
    unittest.main()
