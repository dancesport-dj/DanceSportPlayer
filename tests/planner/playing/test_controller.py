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
            "cart_volume": "cc:0:1",                       # fader 2
            "tempo_reset": "cc:0:32",                      # S1
            "lib": "cc:0:59",                              # TRACK ▶
            "browse_up": "cc:0:61", "browse_down": "cc:0:62",   # MARKER ◀ ▶
            "pick_play": "cc:0:33", "pick_deck": "cc:0:34",     # S2, S3
            "pick_wish": "cc:0:35",                        # S4
            "pad:1": "cc:0:36", "pad:2": "cc:0:52", "pad:3": "cc:0:68",
            "pad:4": "cc:0:37", "pad:5": "cc:0:53", "pad:6": "cc:0:69",
            "pad:7": "cc:0:38", "pad:8": "cc:0:39",
            "pad:9": "cc:0:48", "pad:10": "cc:0:49", "pad:11": "cc:0:50",
            "pad:12": "cc:0:51", "pad:15": "cc:0:54", "pad:16": "cc:0:55"})
        self.assertEqual(pctl.clean_bindings(b), b)  # nothing bound twice


class CartVolumeTest(unittest.TestCase):
    """🎛 The cartwall's own fader, beside the music's."""

    def test_the_fader_takes_every_value_and_is_no_key(self):
        self.assertIn("cart_volume", pctl.CONTINUOUS)
        self.assertNotIn("cart_volume", pctl.KEY_ACTIONS)
        m = pctl.ControllerMap({"cart_volume": "cc:0:1"})
        self.assertEqual(m.feed("cc:0:1", 0.3), [("cart_volume", 0.3)])

    def test_the_steps_have_keys_of_their_own(self):
        keys = pctl.desk_keys({})
        self.assertEqual(keys["cart_vol_up"], ["Ctrl+Alt+Up"])
        self.assertEqual(keys["cart_vol_down"], ["Ctrl+Alt+Down"])
        self.assertEqual(pctl.key_clashes(keys), {})

    def test_the_page_turns_have_keys_beside_the_steps(self):
        """Ctrl+Alt is the wall's: ↑/↓ its volume, ←/→ its pages."""
        keys = pctl.desk_keys({})
        self.assertEqual(keys["cart_page_prev"], ["Ctrl+Alt+Left"])
        self.assertEqual(keys["cart_page_next"], ["Ctrl+Alt+Right"])
        self.assertEqual(pctl.key_clashes(keys), {})

    def test_nano_fader_2_is_the_cartwall(self):
        b = pctl.PRESETS["Korg nanoKONTROL2"]["bindings"]
        self.assertEqual(b["volume"], "cc:0:0")
        self.assertEqual(b["cart_volume"], "cc:0:1")
        self.assertEqual(pctl.clean_bindings(b), b)


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


class FocusTest(unittest.TestCase):
    """🎯 A button per playlist and per wishlist, to bring it in front."""

    def test_every_playlist_and_wishlist_has_a_focus_action(self):
        for n in range(1, 9):
            self.assertIn(f"deck:{n}", pctl.ACTION_IDS)
        for n in range(1, 5):
            self.assertIn(f"wish:{n}", pctl.ACTION_IDS)

    def test_a_focus_action_has_a_desk_key_too(self):
        """Ctrl+1…9 already belong to the 🎛 wall: Alt+1…8 for the playlists,
        Alt+Q W E R, the row below, for the wishlists. No Shift, so no
        keyboard layout turns the digit into a symbol."""
        keys = pctl.desk_keys({})
        self.assertEqual([keys[f"deck:{n}"] for n in range(1, 9)],
                         [[f"Alt+{n}"] for n in range(1, 9)])
        self.assertEqual([keys[f"wish:{n}"] for n in range(1, 5)],
                         [["Alt+Q"], ["Alt+W"], ["Alt+E"], ["Alt+R"]])
        self.assertEqual(pctl.key_clashes(keys), {})


class BrowseTest(unittest.TestCase):
    """🔄 Scrolling through a list from the controller and picking a title."""

    def test_the_browse_buttons_and_picks_are_actions_with_keys(self):
        keys = pctl.desk_keys({})
        self.assertEqual({a: keys[a] for a in ("lib", "browse_up", "browse_down",
                                               "pick_play", "pick_deck",
                                               "pick_wish")},
                         {"lib": ["Alt+L"], "browse_up": ["Alt+Up"],
                          "browse_down": ["Alt+Down"], "pick_play": ["Alt+P"],
                          "pick_deck": ["Alt+A"], "pick_wish": ["Alt+D"]})

    def test_the_browse_knob_is_no_key_and_takes_every_reading(self):
        self.assertIn("browse", pctl.CONTINUOUS)
        self.assertNotIn("browse", pctl.KEY_ACTIONS)
        m = pctl.ControllerMap({"browse": "cc:0:20"})
        self.assertEqual(m.feed("cc:0:20", 1 / 127), [("browse", 1 / 127)])
        self.assertEqual(m.feed("cc:0:20", 1 / 127), [("browse", 1 / 127)])

    def test_only_a_midi_cc_can_be_the_browse_knob(self):
        self.assertTrue(pctl.learnable("browse", "cc:0:20"))
        for control in ("hid:1:3", "hid:1:3:0", "note:0:60", "pb:0"):
            self.assertFalse(pctl.learnable("browse", control), control)

    def test_an_endless_knob_counts_steps_in_either_code(self):
        """1, 2, … right and 127, 126, … left; or 65, 66, … right and
        63, 62, … left."""
        for raw, steps in ((1, 1), (3, 3), (127, -1), (125, -3),
                           (65, 1), (67, 3), (63, -1), (61, -3), (64, 0)):
            self.assertEqual(pctl.encoder_steps(raw / 127), steps, raw)


if __name__ == "__main__":
    unittest.main()
