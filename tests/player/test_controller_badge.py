#!/usr/bin/env python3
"""🎛 A green badge in the status bar while the hardware controller is
connected — as the 📱 Remote pill shows the phone remote's server, so the
desk sees at a glance that the nanoKONTROL2 is there to be used.

Run:  .venv/Scripts/python.exe -m unittest tests.player.test_controller_badge -v
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_controller_badge_"))

from PySide6.QtWidgets import QApplication

from player.window import main_controller
from tests.qt_test_support import reap_widget, stub_window_startup


class _FakeMidi:
    present = {"nanoKONTROL2"}

    def __init__(self, name, on_message):
        if name not in self.present:
            raise OSError(f"MIDI input not found: {name}")
        self.name = name

    def close(self):
        pass


_NANO = {"kind": "midi", "device": "nanoKONTROL2", "profile": "", "bindings": {}}


class ControllerBadgeTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.gui = stub_window_startup(cls, {"app_mode": "both", "controller": _NANO})
        for target, name, value in (
                (main_controller.midi_input, "MidiInput", _FakeMidi),
                (main_controller.midi_input, "list_inputs",
                 lambda: sorted(_FakeMidi.present)),
                (main_controller, "save_settings", mock.Mock())):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            cls.addClassCleanup(patcher.stop)

    def setUp(self):
        _FakeMidi.present = {"nanoKONTROL2"}
        self.win = self.gui.MainWindow()
        self.win._loading_dlg.accept()
        self.addCleanup(reap_widget, self.win)

    def _badge(self):
        return self.win.controller_hub().badge

    def test_a_connected_controller_shows_its_badge(self):
        badge = self._badge()
        self.assertFalse(badge.isHidden())
        self.assertIn("🎛", badge.text())
        self.assertIn("nanoKONTROL2", badge.text())
        self.assertTrue(self.win.statusBar().isAncestorOf(badge))

    def test_it_goes_when_the_controller_does(self):
        _FakeMidi.present = set()
        self.win.set_controller_config(_NANO)
        self.assertTrue(self._badge().isHidden())
        _FakeMidi.present = {"nanoKONTROL2"}
        self.win._ctl_retry.timeout.emit()
        self.win.controller_hub().probe.join(2.0)
        QApplication.processEvents()
        self.assertFalse(self._badge().isHidden())

    def test_no_controller_chosen_no_badge(self):
        self.win.set_controller_config({**_NANO, "device": ""})
        self.assertTrue(self._badge().isHidden())

    def test_a_click_opens_the_controller_window(self):
        with mock.patch.object(self.win, "open_controller_window") as opened:
            self._badge().click()
        opened.assert_called_once_with()


if __name__ == "__main__":
    unittest.main(verbosity=2)
