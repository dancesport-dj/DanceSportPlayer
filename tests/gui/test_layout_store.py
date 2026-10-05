#!/usr/bin/env python3
"""📐 The window layout goes where the rest of the state goes.

Run:  py -m unittest tests.gui.test_layout_store -v

The layout (window size, every divider, the 🎛 cartwall dock's edge and
width) is a QSettings store, in the registry on Windows. A test redirects
the app's state with DANCEPLAYLIST_STATE_DIR — and the layout did not follow.
Every MainWindow a test closed ran save_on_quit and wrote its offscreen
layout over the operator's real one, and the tests that "reset" the layout
cleared the real one. The next start then opened the cartwall at the
first-run width, wider than the operator had dragged it.

`QSettings.setDefaultFormat(IniFormat)` did not help: it only reaches the
`QSettings(parent)` constructor, not `QSettings(organization, application)`.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_layout_store_"))

from pathlib import Path  # noqa: E402

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.main_persist import layout_settings  # noqa: E402
from planner.store import state_dir  # noqa: E402

_app = QApplication.instance() or QApplication(sys.argv)


class LayoutStoreTest(unittest.TestCase):

    def test_a_redirected_state_takes_the_layout_along(self):
        s = layout_settings()
        self.assertEqual(s.format(), QSettings.Format.IniFormat)
        self.assertEqual(Path(s.fileName()).parent.resolve(),
                         state_dir().resolve())

    def test_the_app_itself_keeps_its_layout_where_it_always_was(self):
        """No redirect, no move: the operator's saved layout stays readable."""
        with mock.patch.dict(os.environ):
            os.environ.pop("DANCEPLAYLIST_STATE_DIR")
            s = layout_settings()
            self.assertEqual(s.format(), QSettings.Format.NativeFormat)
            self.assertEqual(s.organizationName(), "danceplaylist_ai")
            self.assertEqual(s.applicationName(), "planner")


if __name__ == "__main__":
    unittest.main()
