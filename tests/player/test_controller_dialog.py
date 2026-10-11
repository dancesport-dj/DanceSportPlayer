"""🎛 The controller's window: device, preset, profile files and learn."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from planner import controller as pctl
from player import controller_dialog
from player.controller_dialog import ControllerDialog
from player.main_controller import _ControllerHub

_DEVICES = [("midi", "nanoKONTROL2", "nanoKONTROL2"),
            ("hid", "17cc:1234", "Native Instruments Traktor (HID)")]


class _Host:
    """What the window asks of the main window, and nothing more."""

    def __init__(self, cfg=None):
        self.hub = _ControllerHub()
        self.cfg = {"kind": "", "device": "", "profile": "", "bindings": {}, **(cfg or {})}
        self.listener = None
        self.saves = 0

    def controller_hub(self):
        return self.hub

    def controller_config(self):
        return {**self.cfg, "bindings": dict(self.cfg["bindings"])}

    def set_controller_config(self, cfg):
        self.cfg = {**cfg, "bindings": pctl.clean_bindings(cfg["bindings"])}
        self.saves += 1
        self.hub.changed.emit()

    def controller_status(self):
        return bool(self.cfg["device"]), self.cfg["device"] or "nothing chosen"

    def set_controller_listener(self, fn):
        self.listener = fn


class ControllerDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        patcher = mock.patch.object(controller_dialog, "controller_devices",
                                    return_value=list(_DEVICES))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.dir = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(controller_dialog, "profile_dir", return_value=self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _dlg(self, host):
        dlg = ControllerDialog(host)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def _row(self, action):
        return pctl.ACTION_IDS.index(action)

    def _control_text(self, dlg, action):
        return dlg._table.item(self._row(action), 1).text()

    def test_every_action_has_a_row(self):
        dlg = self._dlg(_Host())
        self.assertEqual(dlg._table.rowCount(), len(pctl.ACTIONS))
        self.assertEqual(dlg._table.item(self._row("pad:16"), 0).text(),
                         "🎛  Cartwall pad 16")

    def test_choosing_a_device_applies_it(self):
        host = _Host()
        dlg = self._dlg(host)
        dlg._on_device_chosen(2)        # 0 is "— none —"
        self.assertEqual((host.cfg["kind"], host.cfg["device"]), ("hid", "17cc:1234"))
        self.assertIn("Connected", dlg._status.text())

    def test_a_chosen_device_not_plugged_in_is_still_listed(self):
        dlg = self._dlg(_Host({"kind": "midi", "device": "Old box"}))
        self.assertIn("Old box", dlg._device.currentText())
        self.assertIn("not plugged in", dlg._device.currentText())

    def test_the_nano_preset_binds_and_picks_its_device(self):
        host = _Host()
        dlg = self._dlg(host)
        dlg._apply_preset("Korg nanoKONTROL2")
        self.assertEqual(host.cfg["profile"], "Korg nanoKONTROL2")
        self.assertEqual(host.cfg["device"], "nanoKONTROL2")
        self.assertEqual(host.cfg["bindings"]["toggle"], "cc:0:41")
        self.assertEqual(self._control_text(dlg, "toggle"), "CC 41 · ch 1")
        self.assertEqual(dlg._device.currentText(), "nanoKONTROL2")

    def test_learn_waits_for_the_press_then_binds(self):
        host = _Host({"bindings": {"toggle": "cc:0:41"}, "profile": "Korg nanoKONTROL2"})
        dlg = self._dlg(host)
        dlg._learn_btns["next"].click()
        self.assertIsNotNone(host.listener)
        self.assertIn("Press", self._control_text(dlg, "next"))
        host.listener("cc:0:44", 0.0)               # a release: not yet
        self.assertNotIn("next", host.cfg["bindings"])
        host.listener("cc:0:44", 1.0)
        self.assertEqual(host.cfg["bindings"]["next"], "cc:0:44")
        self.assertIsNone(host.listener)
        self.assertEqual(host.cfg["profile"], "")   # edited: no longer the preset
        self.assertFalse(dlg._learn_btns["next"].isChecked())

    def test_learning_a_taken_control_moves_it(self):
        host = _Host({"bindings": {"toggle": "cc:0:41"}})
        dlg = self._dlg(host)
        dlg._learn_btns["fade"].click()
        host.listener("cc:0:41", 1.0)
        self.assertEqual(host.cfg["bindings"], {"fade": "cc:0:41"})
        self.assertEqual(self._control_text(dlg, "toggle"), "")

    def test_a_fader_learns_even_from_its_bottom(self):
        host = _Host()
        dlg = self._dlg(host)
        dlg._learn_btns["volume"].click()
        host.listener("cc:0:0", 0.1)
        self.assertEqual(host.cfg["bindings"], {"volume": "cc:0:0"})

    def test_hid_a_button_learns_a_bit_not_the_byte(self):
        host = _Host()
        dlg = self._dlg(host)
        dlg._learn_btns["next"].click()
        host.listener("hid:1:4", 1.0)
        self.assertEqual(host.cfg["bindings"], {})
        host.listener("hid:1:4:3", 1.0)
        self.assertEqual(host.cfg["bindings"], {"next": "hid:1:4:3"})

    def test_learn_again_or_closing_cancels(self):
        host = _Host()
        dlg = self._dlg(host)
        dlg._learn_btns["next"].click()
        dlg._learn_btns["next"].click()
        self.assertIsNone(host.listener)
        dlg._learn_btns["prev"].click()
        dlg.reject()
        self.assertIsNone(host.listener)
        self.assertEqual(host.cfg["bindings"], {})

    def test_clear_unbinds(self):
        host = _Host({"bindings": {"toggle": "cc:0:41", "next": "cc:0:44"}})
        dlg = self._dlg(host)
        dlg._clear("toggle")
        self.assertEqual(host.cfg["bindings"], {"next": "cc:0:44"})

    def test_save_then_load_a_profile(self):
        host = _Host({"device": "nanoKONTROL2", "kind": "midi",
                      "bindings": {"toggle": "cc:0:41"}})
        dlg = self._dlg(host)
        path = str(self.dir / "Evening.json")
        with mock.patch.object(controller_dialog.QFileDialog, "getSaveFileName",
                               return_value=(path, "")):
            dlg._save_profile()
        self.assertEqual(host.cfg["profile"], "Evening")
        dlg._clear("toggle")
        with mock.patch.object(controller_dialog.QFileDialog, "getOpenFileName",
                               return_value=(path, "")):
            dlg._load_profile()
        self.assertEqual(host.cfg["bindings"], {"toggle": "cc:0:41"})
        self.assertEqual(host.cfg["profile"], "Evening")

    def test_a_broken_profile_file_is_refused_with_a_message(self):
        host = _Host({"bindings": {"toggle": "cc:0:41"}})
        dlg = self._dlg(host)
        bad = self.dir / "bad.json"
        bad.write_text("nope", encoding="utf-8")
        with mock.patch.object(controller_dialog.QFileDialog, "getOpenFileName",
                               return_value=(str(bad), "")), \
             mock.patch.object(controller_dialog.QMessageBox, "warning") as warn:
            dlg._load_profile()
        warn.assert_called_once()
        self.assertEqual(host.cfg["bindings"], {"toggle": "cc:0:41"})

    def test_the_last_reading_names_its_action(self):
        host = _Host({"bindings": {"next": "cc:0:44"}})
        dlg = self._dlg(host)
        host.hub.control.emit("cc:0:44", 1.0)
        self.assertIn("Next title", dlg._last.text())
        host.hub.control.emit("cc:0:9", 0.5)
        self.assertIn("not bound", dlg._last.text())


if __name__ == "__main__":
    unittest.main()
