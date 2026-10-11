"""🎛 Hardware controller, desk side: connecting, retrying, and what each
binding does to the desk."""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from planner import cartwall as pc
from planner import controller as pctl
from player import main_controller
from player.main_controller import ControllerMixin


class _FakeMidi:
    present = {"nanoKONTROL2"}
    opened = []

    def __init__(self, name, on_message):
        if name not in self.present:
            raise OSError(f"MIDI input not found: {name}")
        self.name = name
        self.on_message = on_message
        self.closed = False
        _FakeMidi.opened.append(self)

    def close(self):
        self.closed = True


class _Desk(QObject, ControllerMixin):
    def __init__(self, settings=None):
        super().__init__()
        self._settings = dict(settings or {})
        self._on_remote_command = mock.Mock()
        self._set_base_volume = mock.Mock()
        self._set_desk_duck = mock.Mock()
        self._mix = mock.Mock(desk=1.0)
        self._cartwall = None


class ControllerMixinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        _FakeMidi.opened = []
        _FakeMidi.present = {"nanoKONTROL2"}
        for target, value in (("midi_input.MidiInput", _FakeMidi),
                              ("save_settings", mock.Mock())):
            patcher = mock.patch.object(
                main_controller if "." not in target else main_controller.midi_input,
                target.split(".")[-1], value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _desk(self, bindings=None, device="nanoKONTROL2"):
        desk = _Desk({"controller": {"kind": "midi", "device": device,
                                     "bindings": bindings or {}}})
        desk._init_controller()
        self.addCleanup(desk._controller_shutdown)
        return desk

    def _press(self, desk, cc, value=127):
        desk._emit_midi(desk.controller_hub(), 0xB0, cc, value)

    def test_no_device_chosen_nothing_opens(self):
        desk = _Desk()
        desk._init_controller()
        self.assertEqual(desk.controller_config(),
                         {"kind": "", "device": "", "profile": "", "bindings": {}})
        self.assertEqual(_FakeMidi.opened, [])
        self.assertFalse(desk.controller_status()[0])
        self.assertFalse(desk._ctl_retry.isActive())

    def test_the_chosen_device_opens_at_launch(self):
        desk = self._desk()
        self.assertEqual([m.name for m in _FakeMidi.opened], ["nanoKONTROL2"])
        self.assertEqual(desk.controller_status(), (True, "nanoKONTROL2"))

    def test_a_missing_device_is_retried_until_it_turns_up(self):
        _FakeMidi.present = set()
        desk = self._desk()
        connected, why = desk.controller_status()
        self.assertFalse(connected)
        self.assertIn("not found", why)
        self.assertTrue(desk._ctl_retry.isActive())
        _FakeMidi.present = {"nanoKONTROL2"}
        desk._ctl_retry.timeout.emit()
        self.assertTrue(desk.controller_status()[0])
        self.assertFalse(desk._ctl_retry.isActive())

    def test_a_new_config_is_saved_and_reconnected(self):
        desk = self._desk()
        first = _FakeMidi.opened[0]
        desk.set_controller_config({"kind": "midi", "device": "nanoKONTROL2",
                                    "profile": "Mine", "bindings": {"next": "cc:0:44"}})
        self.assertTrue(first.closed)
        self.assertEqual(len(_FakeMidi.opened), 2)
        main_controller.save_settings.assert_called()
        self.assertEqual(desk._settings["controller"]["profile"], "Mine")
        self._press(desk, 44)
        desk._on_remote_command.assert_called_once_with("next", None)

    def test_the_nano_preset_drives_the_transport_once_per_press(self):
        desk = self._desk(pctl.PRESETS["Korg nanoKONTROL2"]["bindings"])
        self._press(desk, 41)           # PLAY
        self._press(desk, 41, 0)        # its release
        self._press(desk, 44)           # ▶▶
        self._press(desk, 42)           # STOP
        self.assertEqual(desk._on_remote_command.call_args_list,
                         [mock.call("toggle", None), mock.call("next", None),
                          mock.call("fade", None)])

    def test_the_fader_sets_the_music_volume(self):
        desk = self._desk({"volume": "cc:0:0"})
        self._press(desk, 0, 0)
        self._press(desk, 0, 127)
        self.assertEqual(desk._set_base_volume.call_args_list,
                         [mock.call(0.0), mock.call(1.0)])

    def test_duck_toggles_the_desk_duck(self):
        desk = self._desk({"duck": "cc:0:58"})
        self._press(desk, 58)
        desk._set_desk_duck.assert_called_once_with(True)
        desk._mix.desk = 0.3
        self._press(desk, 58, 0)
        self._press(desk, 58)
        desk._set_desk_duck.assert_called_with(False)

    def test_a_pad_is_the_nth_cell_of_the_page_on_screen(self):
        desk = self._desk({"pad:2": "cc:0:33", "pad:3": "cc:0:34"})
        wall = mock.Mock()
        wall.grid.return_value = (2, 8)
        wall.current_page.return_value = 1
        wall.pages.return_value = [pc.Page(name="A", pads={}),
                                   pc.Page(name="B", pads={(0, 1): pc.CartPad(path="x.mp3")})]
        desk._cartwall = wall
        self._press(desk, 33)
        wall.play_pad.assert_called_once_with((1, 0, 1))
        self._press(desk, 34)           # (1, 0): an empty cell stays a hole
        wall.play_pad.assert_called_once()

    def test_a_listener_takes_the_readings_instead_of_the_desk(self):
        desk = self._desk({"next": "cc:0:44"})
        heard = []
        desk.set_controller_listener(lambda c, v: heard.append((c, v)))
        self._press(desk, 44)
        self.assertEqual(heard, [("cc:0:44", 1.0)])
        desk._on_remote_command.assert_not_called()
        desk.set_controller_listener(None)
        self._press(desk, 44, 0)
        self._press(desk, 44)
        desk._on_remote_command.assert_called_once_with("next", None)

    def test_hid_the_first_report_is_the_resting_state(self):
        desk = self._desk({"next": "hid:1:2:0"}, device="")
        desk._on_hid_report(bytes([1, 0, 1]))       # already held: baseline
        desk._on_remote_command.assert_not_called()
        desk._on_hid_report(bytes([1, 0, 0]))
        desk._on_hid_report(bytes([1, 0, 1]))
        desk._on_remote_command.assert_called_once_with("next", None)


if __name__ == "__main__":
    unittest.main()
