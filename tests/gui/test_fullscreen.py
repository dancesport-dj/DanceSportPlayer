"""⛶ F11: the planner and the player fill the screen, with a clock at the
bottom right of the status bar while they do.

Run:  py -m unittest tests.gui.test_fullscreen -v

Marcel: "add a full screen mode for the planner and player. in fullscreen
mode we want the current time and date in the bar at the bottm also right
aligned."
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_fullscreen_"))

from PySide6.QtCore import QDateTime, QDate, QTime
from PySide6.QtWidgets import QApplication

from gui.window.main_fullscreen import clock_text
from planner import i18n
from tests.qt_test_support import reap_widget, stub_window_startup


class FullscreenTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both"})

    def setUp(self):
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        self.win.show()

    def test_f11_switches_it_on_and_off(self):
        sc = self.win._fullscreen_sc
        self.assertEqual(sc.key().toString(), "F11")
        sc.activated.emit()
        self.assertTrue(self.win.isFullScreen())
        sc.activated.emit()
        self.assertFalse(self.win.isFullScreen())

    def test_the_clock_shows_only_in_fullscreen_at_the_right(self):
        win = self.win
        self.assertTrue(win._clock.isHidden())
        win.set_fullscreen(True)
        clock = win._clock
        self.assertFalse(clock.isHidden())
        self.assertTrue(win.statusBar().isAncestorOf(clock))
        # Marcel: "make time not bold".
        self.assertFalse(clock.font().bold())
        self.assertNotIn("bold", clock.styleSheet())
        self.assertTrue(win._clock_timer.isActive())
        self.assertIn(QTime.currentTime().toString("HH:mm"), clock.text())
        win.set_fullscreen(False)
        self.assertTrue(clock.isHidden())
        self.assertFalse(win._clock_timer.isActive())

    def test_the_clock_stays_right_of_the_live_badge(self):
        win = self.win
        win.set_fullscreen(True)
        win._remote = mock.Mock()
        win._sync_remote_badge()
        self.app.processEvents()
        self.assertLess(win._remote_badge.geometry().x(), win._clock.geometry().x())

    def test_the_time_only_setting_drops_the_date(self):
        # Marcel: "and a option in settings to only show 20:45:12 time".
        win = self.win
        win._settings["clock_time_only"] = True
        self.addCleanup(win._settings.pop, "clock_time_only", None)
        win.set_fullscreen(True)
        self.assertRegex(win._clock.text(), r"^\d\d:\d\d:\d\d$")

    def test_the_help_menu_offers_it(self):
        texts = [a.text() for a in self.win._help_menu().actions()]
        self.assertIn("⛶  Fullscreen  (F11)", texts)

    def test_the_menu_entry_says_what_it_does_instead_of_a_tick(self):
        # Marcel: "fullscreen option should not have a checkbox but a label change".
        def entry():
            return next(a for a in self.win._help_menu().actions()
                        if "Fullscreen" in a.text())
        self.assertFalse(entry().isCheckable())
        self.win.set_fullscreen(True)
        self.assertEqual(entry().text(), "⛶  Exit Fullscreen  (F11)")
        self.assertFalse(entry().isCheckable())
        entry().trigger()
        self.assertFalse(self.win.isFullScreen())


class ClockTextTest(unittest.TestCase):

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def test_short_date_and_time_with_seconds(self):
        # Marcel: "make the time in fullscreen short like Sat, 10.10.2026 20:45:12".
        when = QDateTime(QDate(2026, 10, 10), QTime(20, 45, 12))
        self.assertEqual(clock_text(when), "Sat, 10.10.2026 20:45:12")
        i18n.set_active("de")        # Qt's "Sa." loses its dot before the comma
        self.assertEqual(clock_text(when), "Sa, 10.10.2026 20:45:12")

    def test_time_only(self):
        when = QDateTime(QDate(2026, 10, 10), QTime(20, 45, 12))
        self.assertEqual(clock_text(when, time_only=True), "20:45:12")


class ClockSettingTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_box_on_look_off_by_default(self):
        from PySide6.QtWidgets import QTabWidget
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog({}, None)
        self.addCleanup(dlg.deleteLater)
        tabs = dlg.findChild(QTabWidget)
        page = next(tabs.widget(i) for i in range(tabs.count())
                    if tabs.tabText(i) == "🎨 Look")
        self.assertTrue(page.isAncestorOf(dlg._clock_time_only_chk))
        self.assertFalse(dlg._clock_time_only_chk.isChecked())
        self.assertFalse(dlg.values()["clock_time_only"])
        dlg._clock_time_only_chk.setChecked(True)
        self.assertTrue(dlg.values()["clock_time_only"])
        dlg = SettingsDialog({"clock_time_only": True}, None)
        self.addCleanup(dlg.deleteLater)
        self.assertTrue(dlg._clock_time_only_chk.isChecked())


if __name__ == "__main__":
    unittest.main()
