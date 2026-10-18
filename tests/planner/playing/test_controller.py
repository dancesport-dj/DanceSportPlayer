"""🎛 Controller profiles: naming controls, binding them, firing once per press."""
import json
import tempfile
import unittest
from pathlib import Path

from planner.playing import controller as pctl


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

    def test_a_midi_cc_fits_either(self):
        self.assertTrue(pctl.learnable("volume", "cc:0:0"))
        self.assertTrue(pctl.learnable("toggle", "cc:0:41"))

    def test_a_key_is_a_button_a_bend_is_a_fader(self):
        self.assertTrue(pctl.learnable("next", "note:0:36"))
        self.assertFalse(pctl.learnable("volume", "note:0:36"))
        self.assertTrue(pctl.learnable("tempo", "pb:0"))
        self.assertFalse(pctl.learnable("next", "pb:0"))


class LearnTakesTest(unittest.TestCase):
    """A CC is a button or a knob, and only how it moves tells which."""

    def test_a_button_jumps_to_its_top(self):
        self.assertTrue(pctl.learn_takes("next", "cc:0:44", 1.0, set()))
        self.assertFalse(pctl.learn_takes("next", "cc:0:44", 0.0, set()))

    def test_a_knob_swept_to_its_top_is_no_press(self):
        swept = set()
        for value in (0.4, 0.6, 0.9):
            self.assertFalse(pctl.learn_takes("next", "cc:0:16", value, swept))
        self.assertFalse(pctl.learn_takes("next", "cc:0:16", 1.0, swept))

    def test_a_button_is_no_fader(self):
        swept = set()
        self.assertFalse(pctl.learn_takes("volume", "cc:0:41", 1.0, swept))
        self.assertFalse(pctl.learn_takes("volume", "cc:0:41", 0.0, swept))

    def test_a_fader_takes_its_first_step_between(self):
        self.assertTrue(pctl.learn_takes("volume", "cc:0:0", 0.1, set()))

    def test_another_control_sweeping_does_not_spoil_a_button(self):
        swept = set()
        pctl.learn_takes("next", "cc:0:16", 0.5, swept)
        self.assertTrue(pctl.learn_takes("next", "cc:0:44", 1.0, swept))


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
    def test_the_preset_is_the_layout_played_at_the_desk(self):
        # Marcel: "for the nanocontrol default setting use the current saved
        # custom preset" — the mapping saved in gui_settings.json, 2026-10-17.
        b = pctl.PRESETS["Korg nanoKONTROL2"]["bindings"]
        self.assertEqual(b, {
            "toggle": "cc:0:41", "fade": "cc:0:42",        # PLAY, STOP
            "prev": "cc:0:43", "next": "cc:0:44",          # ◀◀, ▶▶
            "hold": "cc:0:45", "announce": "cc:0:46",      # ●, CYCLE
            "duck": "cc:0:58", "stop_pads": "cc:0:60",     # TRACK ◀, SET
            "volume": "cc:0:0", "tempo": "cc:0:16",        # fader 1, knob 1
            "tempo_reset": "cc:0:32",                      # S1
            "pad:1": "cc:0:36", "pad:2": "cc:0:52", "pad:3": "cc:0:68",
            "pad:4": "cc:0:37", "pad:5": "cc:0:53", "pad:6": "cc:0:69",
            "pad:7": "cc:0:38", "pad:8": "cc:0:39",
            "pad:9": "cc:0:48", "pad:10": "cc:0:49", "pad:11": "cc:0:50",
            "pad:12": "cc:0:51", "pad:15": "cc:0:54", "pad:16": "cc:0:55"})
        self.assertEqual(pctl.clean_bindings(b), b)  # nothing bound twice


class TempoTest(unittest.TestCase):
    """🎚 The tempo fader from a knob, buttons or keys."""

    def test_the_knob_takes_every_value_and_is_no_key(self):
        self.assertIn("tempo", pctl.CONTINUOUS)
        self.assertNotIn("tempo", pctl.KEY_ACTIONS)
        m = pctl.ControllerMap({"tempo": "cc:0:16"})
        self.assertEqual(m.feed("cc:0:16", 0.7), [("tempo", 0.7)])
        self.assertEqual(m.feed("cc:0:16", 0.6), [("tempo", 0.6)])

    def test_a_hid_byte_can_be_the_knob(self):
        self.assertTrue(pctl.learnable("tempo", "hid:1:3"))
        self.assertFalse(pctl.learnable("tempo", "hid:1:3:0"))

    def test_steps_and_reset_have_keys(self):
        keys = pctl.desk_keys({})
        self.assertEqual(keys["tempo_up"], ["Ctrl+Shift+PgUp"])
        self.assertEqual(keys["tempo_down"], ["Ctrl+Shift+PgDown"])
        self.assertEqual(keys["tempo_reset"], ["Ctrl+Shift+Home"])
        self.assertEqual(pctl.key_clashes(keys), {})

    def test_the_knob_spans_the_whole_fader(self):
        self.assertEqual(pctl.knob_offset(0.0), -1.0)
        self.assertEqual(pctl.knob_offset(1.0), 1.0)

    def test_the_middle_of_a_7_bit_knob_is_zero(self):
        """0…127 has no middle step: 63 and 64 straddle it. Turned back to
        the middle, the tempo is ±0 %, not ±0.1 %."""
        self.assertEqual(pctl.knob_offset(63 / 127), 0.0)
        self.assertEqual(pctl.knob_offset(64 / 127), 0.0)
        self.assertLess(pctl.knob_offset(62 / 127), 0.0)
        self.assertGreater(pctl.knob_offset(65 / 127), 0.0)

    def test_the_middle_of_a_hid_byte_and_a_bend_is_zero(self):
        self.assertEqual(pctl.knob_offset(127 / 255), 0.0)
        self.assertEqual(pctl.knob_offset(128 / 255), 0.0)
        self.assertEqual(pctl.knob_offset(8192 / 16383), 0.0)


if __name__ == "__main__":
    unittest.main()
