"""A damaged view setting must not stop the window opening (review item 43).

`compact` and `wish_state` in gui_settings.json were read with a bare int(),
so a hand-edited "x" or a null raised ValueError out of MainWindow().

Run:  py -m unittest tests.gui.test_garbled_view_settings -v
"""
import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_garbled_"))

from tests.qt_test_support import reap_widget, stub_window_startup


class GarbledViewSettingsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication

        QSettings.setDefaultFormat(QSettings.Format.IniFormat)
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          tempfile.mkdtemp(prefix="dp_garbled_qs_"))
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls)

    def _win(self, **extra):
        self.gui.load_settings = lambda *a, **kw: dict({"app_mode": "both"}, **extra)
        win = self.gui.MainWindow()
        win._loading_dlg.accept()   # closeEvent blocks a plain close()
        self.addCleanup(reap_widget, win)
        return win

    def test_a_non_number_compact_state_falls_back_to_full(self):
        for value in ("x", [1], {"a": 1}):
            with self.subTest(value=value):
                self.assertEqual(self._win(compact=value)._compact_state, 0)

    def test_a_non_number_wishlist_state_falls_back_to_one(self):
        for value in ("x", None, [2]):
            with self.subTest(value=value):
                self.assertEqual(self._win(wish_state=value)._wish_state, 1)


if __name__ == "__main__":
    unittest.main()
