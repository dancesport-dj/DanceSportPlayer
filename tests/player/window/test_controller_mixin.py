"""🎛 Hardware controller, desk side: connecting, retrying, and what each
binding does to the desk."""
import os
import threading
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from planner.playing import cartwall as pc
from planner.playing import controller as pctl
from player.window import main_controller
from player.window.main_controller import ControllerMixin


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
        self._set_cart_volume = mock.Mock()
        self._set_desk_duck = mock.Mock()
        self._mix = mock.Mock(desk=1.0, cart=0.5)
        self._cartwall = None
        self._big_player = mock.Mock()
        self._focus_list = mock.Mock()


class ControllerMixinTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        _FakeMidi.opened = []
        _FakeMidi.present = {"nanoKONTROL2"}
        for target, value in (("midi_input.MidiInput", _FakeMidi),
                              ("midi_input.list_inputs", lambda: sorted(_FakeMidi.present)),
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

    def _tick(self, desk):
        """One retry/watch tick, and its look at the device list finished."""
        desk._ctl_retry.timeout.emit()
        probe = desk.controller_hub().probe
        if probe is not None:
            probe.join(2.0)
        QApplication.processEvents()

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
        self._tick(desk)
        self.assertTrue(desk.controller_status()[0])
        self.assertTrue(desk._ctl_retry.isActive())     # now watching for an unplug

    def test_an_unplugged_device_is_noticed_and_comes_back(self):
        # Marcel: "why is unplugg not detected, can we not detect it" — no
        # backend reports a USB unplug, so the tick looks for it in the list.
        desk = self._desk()
        first = _FakeMidi.opened[0]
        self.assertTrue(desk._ctl_retry.isActive())
        news = mock.Mock()
        desk.controller_hub().changed.connect(news)
        _FakeMidi.present = set()
        self._tick(desk)
        connected, why = desk.controller_status()
        self.assertFalse(connected)
        self.assertIn("not found", why)
        self.assertTrue(first.closed)
        news.assert_called()
        self.assertTrue(desk._ctl_retry.isActive())
        _FakeMidi.present = {"nanoKONTROL2"}
        self._tick(desk)
        self.assertTrue(desk.controller_status()[0])
        self.assertEqual(len(_FakeMidi.opened), 2)

    def test_a_device_still_plugged_in_is_left_alone(self):
        desk = self._desk()
        self._tick(desk)
        self._tick(desk)
        self.assertEqual(len(_FakeMidi.opened), 1)
        self.assertFalse(_FakeMidi.opened[0].closed)
        self.assertTrue(desk.controller_status()[0])

    def test_an_unplugged_hid_device_is_noticed_too(self):
        # Its reader thread ends on the read error an unplug brings, so the
        # tick never runs the HID enumeration (about 250 ms on the GUI thread).
        hid_dev = mock.Mock(alive=True)
        hid_dev.name = "17cc:1500"
        plugged = [True]

        def open_hid(ident, on_report):
            if not plugged[0]:
                raise OSError(f"HID device not found: {ident}")
            return hid_dev

        enumerate_hid = mock.Mock(side_effect=AssertionError("enumerated on the tick"))
        with (mock.patch.object(main_controller.hid_input, "HidInput", open_hid),
              mock.patch.object(main_controller.hid_input, "list_devices", enumerate_hid)):
            desk = _Desk({"controller": {"kind": "hid", "device": "17cc:1500",
                                         "bindings": {}}})
            desk._init_controller()
            self.addCleanup(desk._controller_shutdown)
            self._tick(desk)
            hid_dev.close.assert_not_called()
            self.assertTrue(desk.controller_status()[0])
            hid_dev.alive = False
            plugged[0] = False
            self._tick(desk)
            hid_dev.close.assert_called_once_with()
            self.assertFalse(desk.controller_status()[0])

    def _hid_desk(self, plugged, opened):
        """A HID desk whose device is in the list while `plugged[0]`; every
        open is recorded in `opened` as (thread, device)."""

        def open_hid(ident, on_report):
            if not plugged[0]:
                raise OSError(f"HID device not found: {ident}")
            dev = mock.Mock(alive=True)
            dev.name = ident
            opened.append((threading.current_thread(), dev))
            return dev

        for name, value in (("HidInput", open_hid),
                            ("list_devices", lambda all_hid=False:
                             [("17cc:1500", "Traktor")] if plugged[0] else [])):
            patcher = mock.patch.object(main_controller.hid_input, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        desk = _Desk({"controller": {"kind": "hid", "device": "17cc:1500",
                                     "bindings": {}}})
        desk._init_controller()
        self.addCleanup(desk._controller_shutdown)
        return desk

    def test_a_replugged_hid_device_is_opened_off_the_gui_thread(self):
        # Opening a HID device enumerates and opens it, about 250 ms — on a
        # re-plug that is the probe thread's work, not the music's thread.
        plugged, opened = [False], []
        desk = self._hid_desk(plugged, opened)
        self.assertFalse(desk.controller_status()[0])
        plugged[0] = True
        self._tick(desk)
        self.assertEqual(desk.controller_status(), (True, "17cc:1500"))
        self.assertEqual(len(opened), 1)
        self.assertIsNot(opened[0][0], threading.main_thread())

    def test_a_late_open_for_a_device_no_longer_chosen_is_closed(self):
        plugged, opened = [False], []
        desk = self._hid_desk(plugged, opened)
        plugged[0] = True
        desk._ctl_retry.timeout.emit()
        desk.controller_hub().probe.join(2.0)
        desk._settings["controller"] = {"kind": "", "device": "", "bindings": {}}
        QApplication.processEvents()
        self.assertFalse(desk.controller_status()[0])
        opened[0][1].close.assert_called_once_with()

    def test_the_device_list_is_read_off_the_gui_thread(self):
        # Marcel: "can the check be not on the gui thread? we must make sure
        # that music playback is not interruppted"
        readers = []

        def list_inputs():
            readers.append(threading.current_thread())
            return sorted(_FakeMidi.present)

        desk = self._desk()
        with mock.patch.object(main_controller.midi_input, "list_inputs", list_inputs):
            self._tick(desk)
        self.assertTrue(readers)
        self.assertNotIn(threading.main_thread(), readers)

    def test_a_late_answer_for_another_device_is_ignored(self):
        desk = self._desk()
        desk.controller_hub().found.emit("someOtherDevice", False)
        QApplication.processEvents()
        self.assertTrue(desk.controller_status()[0])

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

    def test_nano_fader_2_sets_the_cartwall_volume(self):
        desk = self._desk(pctl.PRESETS["Korg nanoKONTROL2"]["bindings"])
        self._press(desk, 1, 0)
        self._press(desk, 1, 127)
        self.assertEqual(desk._set_cart_volume.call_args_list,
                         [mock.call(0.0), mock.call(1.0)])
        desk._set_base_volume.assert_not_called()

    def test_cartwall_volume_buttons_step_it(self):
        desk = self._desk({"cart_vol_up": "cc:0:64", "cart_vol_down": "cc:0:65"})
        self._press(desk, 64)
        self._press(desk, 65)
        self.assertEqual(desk._set_cart_volume.call_args_list,
                         [mock.call(0.5 + pctl.VOLUME_STEP),
                          mock.call(0.5 - pctl.VOLUME_STEP)])

    def test_the_nano_knob_above_fader_1_moves_the_tempo(self):
        desk = self._desk(pctl.PRESETS["Korg nanoKONTROL2"]["bindings"])
        self._press(desk, 16, 0)
        self._press(desk, 16, 127)
        self._press(desk, 16, 64)
        self.assertEqual(desk._big_player.set_tempo_from_knob.call_args_list,
                         [mock.call(-1.0), mock.call(1.0), mock.call(0.0)])

    def test_tempo_buttons_step_and_reset(self):
        desk = self._desk({"tempo_up": "cc:0:64", "tempo_down": "cc:0:65",
                           "tempo_reset": "cc:0:66"})
        for cc in (64, 65, 66):
            self._press(desk, cc)
        player = desk._big_player
        self.assertEqual(player.step_tempo.call_args_list,
                         [mock.call(True), mock.call(False)])
        player.reset_tempo.assert_called_once_with()

    def test_tempo_without_a_player_does_nothing(self):
        desk = self._desk({"tempo": "cc:0:16", "tempo_up": "cc:0:64"})
        desk._big_player = None
        self._press(desk, 16, 100)
        self._press(desk, 64)
        desk._on_remote_command.assert_not_called()

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

    def test_a_focus_button_brings_its_list_in_front(self):
        desk = self._desk({"deck:2": "cc:0:41", "wish:3": "cc:0:42"})
        self._press(desk, 41)
        desk._focus_list.assert_called_once_with("deck", 2)
        self._press(desk, 42)
        desk._focus_list.assert_called_with("wish", 3)
        desk._on_remote_command.assert_not_called()

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



class HidInputAliveTest(unittest.TestCase):
    """The reader thread ends on a read error, the way hidapi reports an
    unplug, and `alive` says so."""

    def test_a_read_error_ends_the_reader(self):
        from shared.controllers import hid_input

        class _Dev:
            def open_path(self, path):
                pass

            def read(self, size, timeout):
                raise OSError("read error")

            def close(self):
                pass

        fake_hid = mock.Mock()
        fake_hid.enumerate.return_value = [
            {"vendor_id": 0x17CC, "product_id": 0x1500, "path": b"p", "usage_page": 0xFF01}]
        fake_hid.device = _Dev
        with mock.patch.object(hid_input, "hid", fake_hid):
            dev = hid_input.HidInput("17cc:1500", lambda report: None)
            dev._thread.join(timeout=2.0)
            self.assertFalse(dev.alive)
            dev.close()


if __name__ == "__main__":
    unittest.main()
