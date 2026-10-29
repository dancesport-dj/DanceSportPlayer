"""📱 ⚙ Settings → General: the phone remote's pane and its Start Server."""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_phone_remote_"))

from PySide6.QtWidgets import QApplication, QDialog

import dancesport_gui as gui
from gui.dialogs.settings_dialog import SettingsDialog
from gui.window import main_global
from tests.qt_test_support import reap_widget


class PhoneRemoteSettingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _dlg(self, settings):
        dlg = SettingsDialog(settings, None)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_a_pane_of_its_own_with_no_box_to_tick(self):
        # The box said the server starts "when you press OK" — on a dialog
        # whose button says Save. The server is switched in its window now.
        dlg = SettingsDialog({}, None, remote_cb=mock.Mock())
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg._remote_box.title(), "📱  Phone remote")
        self.assertFalse(hasattr(dlg, "_remote_chk"))
        self.assertFalse(hasattr(dlg, "_remote_new_pin_btn"))
        self.assertNotIn("OK", dlg._remote_info.text())
        vals = dlg.values()
        self.assertNotIn("phone_remote", vals)
        self.assertNotIn("remote_pin", vals)

    def test_no_host_no_pane(self):
        self.assertTrue(self._dlg({})._remote_box.isHidden())

    def test_start_server_keeps_the_settings_open(self):
        opened = mock.Mock()
        dlg = SettingsDialog({}, None, remote_cb=opened)
        self.addCleanup(dlg.deleteLater)
        self.assertEqual(dlg._remote_window_btn.text(), "📱  Start Server")
        dlg._remote_window_btn.click()
        opened.assert_called_once_with(dlg)
        self.assertEqual(dlg.result(), 0)        # neither accepted nor rejected

    def test_a_running_server_offers_stop_server(self):
        # Marcel: "Start Server should renamed to Stop Server if Server running".
        from player.window.main_remote import RemoteHub
        hub = RemoteHub()
        running = [True]
        start, stop = mock.Mock(), mock.Mock(side_effect=lambda: running.clear())
        dlg = SettingsDialog({}, None, remote_cb=start,
                             remote_running=lambda: bool(running),
                             remote_stop_cb=stop, remote_changed=hub.changed)
        self.addCleanup(dlg.deleteLater)
        btn = dlg._remote_window_btn
        self.assertEqual(btn.text(), "📱  Stop Server")
        btn.click()
        stop.assert_called_once_with()
        start.assert_not_called()
        self.assertEqual(btn.text(), "📱  Start Server")
        running.append(True)            # started from the server's own window
        hub.changed.emit()
        self.assertEqual(btn.text(), "📱  Stop Server")


class _Dialog:
    """⚙ Settings, saved with whatever the operator changed."""

    values_out = {}

    def __init__(self, settings, parent, **_kw):
        self._given = dict(settings)

    def exec(self):
        return QDialog.DialogCode.Accepted

    def values(self):
        return {**self._given, **self.values_out}

    def running_look_touched(self):
        return False

    def deleteLater(self):
        pass


class SaveAppliesTest(unittest.TestCase):
    """Saving ⚙ Settings no longer switches the server; Start Server does."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        patcher = mock.patch.object(
            gui, "load_settings",
            lambda *a, **kw: {"app_mode": "both", "remote_pin": "4711"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.win = gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)
        for name, value in (("SettingsDialog", _Dialog),
                            ("save_settings", lambda s: None)):
            patch = mock.patch.object(main_global, name, value)
            patch.start()
            self.addCleanup(patch.stop)

    def test_off_by_default_no_server(self):
        self.assertIsNone(self.win._remote)

    def test_saving_leaves_the_server_alone(self):
        # It is the 📱 window's to switch — Settings no longer carries it.
        _Dialog.values_out = {}
        self.win._remote_wanted = True
        with mock.patch.object(self.win, "_apply_remote") as apply:
            self.win._open_settings()
        apply.assert_not_called()
        self.assertTrue(self.win._remote_wanted)

    def test_start_server_starts_it_and_opens_the_window_over_settings(self):
        over = QDialog()
        self.addCleanup(reap_widget, over)
        with mock.patch.object(self.win, "set_remote_running") as run:
            dlg = self.win.start_remote_server(over)
        run.assert_called_once_with(True)
        self.assertIs(dlg.parent(), over)
        self.assertTrue(dlg.isVisible())
        self.assertIsNone(getattr(self.win, "_remote_dlg", None))

    def test_a_green_live_badge_shows_while_the_server_runs(self):
        win = self.win
        with mock.patch.object(win, "_start_remote",
                               lambda: setattr(win, "_remote", mock.Mock())), \
                mock.patch.object(win, "_stop_remote",
                                  lambda: setattr(win, "_remote", None)):
            win._remote_wanted = True
            win._apply_remote()
            badge = win._remote_badge
            self.assertFalse(badge.isHidden())
            # Marcel: "rename live from phone remote to remote to make it
            # diff to nanacontrol" — the 🎛 badge sits next to it.
            self.assertEqual("📱 Remote", badge.text())
            self.assertTrue(win.statusBar().isAncestorOf(badge))
            win._remote_wanted = False
            win._apply_remote()
            self.assertTrue(badge.isHidden())

    def test_clicking_the_live_badge_opens_the_servers_window(self):
        # Marcel: "if i cklick the live badge i want the dialog open".
        win = self.win
        with mock.patch.object(win, "_start_remote",
                               lambda: setattr(win, "_remote", mock.Mock())),                 mock.patch.object(win, "open_remote_window") as opened:
            win._remote_wanted = True
            win._apply_remote()
            win._remote_badge.click()
        opened.assert_called_once_with()
        self.addCleanup(setattr, win, "_remote", None)

    def test_the_closed_dialog_is_deleted_after_it_was_read(self):
        """L6: it hangs off the main window and was never deleted, so every
        opening left one more dialog alive, still following the remote hub.
        Not before values(): Qt runs a deferred delete as exec() returns."""
        for code in (QDialog.DialogCode.Accepted, QDialog.DialogCode.Rejected):
            calls = []

            class _Kept(_Dialog):
                def exec(self):
                    return code

                def values(self):
                    calls.append("values")
                    return super().values()

                def deleteLater(self):
                    calls.append("deleted")

            with self.subTest(code=code),                     mock.patch.object(main_global, "SettingsDialog", _Kept),                     mock.patch.object(self.win, "_offer_settings_restart"):
                self.win._open_settings()
                self.assertEqual(calls[-1:], ["deleted"])
                self.assertEqual(calls.count("deleted"), 1)

    def test_settings_learns_whether_the_server_runs(self):
        seen = {}

        class _Capture(_Dialog):
            def __init__(self, settings, parent, **kw):
                super().__init__(settings, parent)
                seen.update(kw)

        with mock.patch.object(main_global, "SettingsDialog", _Capture):
            self.win._open_settings()
        self.assertFalse(seen["remote_running"]())
        self.win._remote = mock.Mock()
        self.addCleanup(setattr, self.win, "_remote", None)
        self.assertTrue(seen["remote_running"]())
        with mock.patch.object(self.win, "set_remote_running") as run:
            seen["remote_stop_cb"]()
        run.assert_called_once_with(False)
        self.assertIs(seen["remote_changed"], self.win.remote_hub().changed)

    def test_closing_the_window_stops_it(self):
        with mock.patch.object(self.win, "_stop_remote") as stop:
            self.win.close()
        stop.assert_called()


class NotRememberedTest(unittest.TestCase):
    """The server lives as long as the app: closing it stops the server, and
    the next launch starts without one. Marcel: "it is nothing we remember in
    session state persisted to json". An older build saved Start / Stop as
    `phone_remote`, and launching with it on crashed (`_all_tables`)."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_server_saved_as_on_by_an_older_build_is_not_started(self):
        settings = {"app_mode": "both", "remote_pin": "4711",
                    "phone_remote": True, "remote_port": 0}
        with mock.patch.object(gui, "load_settings", lambda *a, **kw: dict(settings)):
            win = gui.MainWindow()
        win._loading_dlg.accept()
        self.addCleanup(reap_widget, win)
        self.assertIsNone(win._remote)
        self.assertFalse(win._remote_wanted)
        self.assertNotIn("phone_remote", win._settings)


if __name__ == "__main__":
    unittest.main()
