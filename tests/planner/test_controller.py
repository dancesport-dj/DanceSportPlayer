"""🎛 Controller profiles: naming controls, binding them, firing once per press."""
import json
import tempfile
import unittest
from pathlib import Path

from planner import controller as pctl


class MidiControlTest(unittest.TestCase):
    def test_cc_note_and_bend_are_named_with_their_channel(self):
        self.assertEqual(pctl.midi_control(0xB0, 41, 127), ("cc:0:41", 1.0))
        self.assertEqual(pctl.midi_control(0xB3, 7, 0), ("cc:3:7", 0.0))
        self.assertEqual(pctl.midi_control(0x91, 60, 127), ("note:1:60", 1.0))
        self.assertEqual(pctl.midi_control(0xE0, 0x7F, 0x7F), ("pb:0", 1.0))

    def test_note_off_is_the_same_control_released(self):
        self.assertEqual(pctl.midi_control(0x81, 60, 64), ("note:1:60", 0.0))

    def test_anything_else_is_not_a_control(self):
        self.assertIsNone(pctl.midi_control(0xF8, 0, 0))       # clock
        self.assertIsNone(pctl.midi_control(0xD0, 30, 0))      # aftertouch


class HidControlsTest(unittest.TestCase):
    def test_a_flipped_bit_yields_the_byte_and_the_bit(self):
        out = pctl.hid_controls(bytes([1, 0, 0]), bytes([1, 0, 0b100]))
        self.assertEqual(out, [("hid:1:2", 4 / 255), ("hid:1:2:2", 1.0)])

    def test_unchanged_bytes_say_nothing(self):
        self.assertEqual(pctl.hid_controls(bytes([1, 9, 9]), bytes([1, 9, 9])), [])

    def test_a_released_bit_reads_zero(self):
        out = dict(pctl.hid_controls(bytes([2, 0b1]), bytes([2, 0])))
        self.assertEqual(out["hid:2:1:0"], 0.0)

    def test_a_longer_report_compares_against_zero(self):
        out = dict(pctl.hid_controls(bytes([1]), bytes([1, 255])))
        self.assertEqual(out["hid:1:1"], 1.0)


class LearnableTest(unittest.TestCase):
    def test_a_hid_byte_only_for_the_volume_a_hid_bit_only_for_buttons(self):
        self.assertTrue(pctl.learnable("volume", "hid:1:3"))
        self.assertFalse(pctl.learnable("volume", "hid:1:3:0"))
        self.assertTrue(pctl.learnable("next", "hid:1:3:0"))
        self.assertFalse(pctl.learnable("next", "hid:1:3"))

    def test_midi_fits_either(self):
        self.assertTrue(pctl.learnable("volume", "cc:0:0"))
        self.assertTrue(pctl.learnable("toggle", "cc:0:41"))


class BindingsTest(unittest.TestCase):
    def test_clean_drops_unknown_actions_and_a_control_bound_twice(self):
        raw = {"toggle": "cc:0:41", "next": "cc:0:41", "bogus": "cc:0:1",
               "prev": 5, "fade": ""}
        self.assertEqual(pctl.clean_bindings(raw), {"toggle": "cc:0:41"})
        self.assertEqual(pctl.clean_bindings(None), {})

    def test_bind_moves_a_control_off_its_old_action(self):
        out = pctl.bind({"toggle": "cc:0:41", "next": "cc:0:44"}, "prev", "cc:0:41")
        self.assertEqual(out, {"next": "cc:0:44", "prev": "cc:0:41"})

    def test_labels(self):
        self.assertEqual(pctl.control_label("cc:0:41"), "CC 41 · ch 1")
        self.assertEqual(pctl.control_label("note:9:36"), "Note 36 · ch 10")
        self.assertEqual(pctl.control_label("hid:1:4:2"), "HID 1 · byte 4 · bit 2")
        self.assertEqual(pctl.control_label("odd"), "odd")


class ProfileFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_save_then_load_round_trips(self):
        path = self.dir / "nano.json"
        pctl.save_profile(path, "Mine", "nanoKONTROL2",
                          {"toggle": "cc:0:41", "volume": "cc:0:0"})
        doc = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(doc["version"], pctl.PROFILE_VERSION)
        self.assertEqual(pctl.load_profile(path),
                         {"name": "Mine", "device": "nanoKONTROL2",
                          "bindings": {"toggle": "cc:0:41", "volume": "cc:0:0"}})

    def test_a_file_without_bindings_is_refused(self):
        path = self.dir / "x.json"
        path.write_text('{"name": "x"}', encoding="utf-8")
        with self.assertRaises(ValueError):
            pctl.load_profile(path)
        path.write_text("not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            pctl.load_profile(path)


class ControllerMapTest(unittest.TestCase):
    def test_a_button_fires_once_on_the_press_not_on_the_release(self):
        m = pctl.ControllerMap({"next": "cc:0:44"})
        self.assertEqual(m.feed("cc:0:44", 1.0), [("next", 1.0)])
        self.assertEqual(m.feed("cc:0:44", 1.0), [])
        self.assertEqual(m.feed("cc:0:44", 0.0), [])
        self.assertEqual(m.feed("cc:0:44", 1.0), [("next", 1.0)])

    def test_the_volume_takes_every_value(self):
        m = pctl.ControllerMap({"volume": "cc:0:0"})
        self.assertEqual(m.feed("cc:0:0", 0.2), [("volume", 0.2)])
        self.assertEqual(m.feed("cc:0:0", 0.1), [("volume", 0.1)])

    def test_an_unbound_control_does_nothing(self):
        self.assertEqual(pctl.ControllerMap({}).feed("cc:0:1", 1.0), [])


class NanoPresetTest(unittest.TestCase):
    def test_the_factory_cc_layout(self):
        b = pctl.PRESETS["Korg nanoKONTROL2"]["bindings"]
        self.assertEqual(b["toggle"], "cc:0:41")     # PLAY
        self.assertEqual(b["fade"], "cc:0:42")       # STOP
        self.assertEqual(b["prev"], "cc:0:43")       # ◀◀
        self.assertEqual(b["next"], "cc:0:44")       # ▶▶
        self.assertEqual(b["volume"], "cc:0:0")      # fader 1
        self.assertEqual(b["pad:1"], "cc:0:32")      # S1
        self.assertEqual(b["pad:8"], "cc:0:39")      # S8
        self.assertEqual(b["pad:9"], "cc:0:48")      # M1
        self.assertEqual(b["pad:16"], "cc:0:55")     # M8
        self.assertEqual(pctl.clean_bindings(b), b)  # nothing bound twice


if __name__ == "__main__":
    unittest.main()
