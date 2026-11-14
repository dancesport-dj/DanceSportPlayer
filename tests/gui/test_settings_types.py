"""⚙ A setting with the wrong type falls back to its default on load (7.D).

Run:  py -m unittest tests.gui.test_settings_types -v

gui_settings.json travels: hand edits, another version, a venue pack from
another machine. A list where the window expects a dict, or a string where it
expects a number, used to stop the window constructor, so the app did not
come up until the file was repaired by hand. load_settings now keeps a stored
value only when it has the type of its default.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_settings_types_"))

from gui.dialogs import load_settings


def _load(data):
    with mock.patch("gui.dialogs.SETTINGS.read", return_value=data):
        return load_settings()


class SettingsTypesTest(unittest.TestCase):

    def test_the_four_values_that_stopped_the_start_fall_back(self):
        # The variants that raised in the window constructor (review 7.D).
        cases = (("column_widths", [1, 2], {}),
                 ("column_order", "abc", None),
                 ("master_volume", "loud", None),
                 ("master_volume", None, None),
                 ("cartwall_volume", "loud", None),
                 ("short_dances", [True], {}))
        for key, bad, want in cases:
            with self.subTest(key=key, bad=bad):
                s = _load({key: bad})
                self.assertEqual(s.get(key), want)

    def test_a_number_default_takes_an_int_or_a_float(self):
        s = _load({"check_min_play_secs": 90.0, "master_volume": 1,
                   "cartwall_volume": 0.4})
        self.assertEqual(s["check_min_play_secs"], 90.0)
        self.assertEqual(s["master_volume"], 1)
        self.assertEqual(s["cartwall_volume"], 0.4)

    def test_a_bool_is_no_number_and_a_number_no_bool(self):
        s = _load({"check_min_play_secs": True, "keep_awake": 0})
        self.assertEqual(s["check_min_play_secs"], 105)
        self.assertIs(s["keep_awake"], True)

    def test_well_typed_and_unknown_keys_are_kept(self):
        s = _load({"keep_awake": False, "player_layout": "tabs",
                   "column_order": {"playlist": [0, 1]}, "some_new_key": [1]})
        self.assertIs(s["keep_awake"], False)
        self.assertEqual(s["player_layout"], "tabs")
        self.assertEqual(s["column_order"]["playlist"][:2], [0, 1])
        self.assertEqual(s["some_new_key"], [1])

    def test_a_replaced_value_is_named_in_the_log(self):
        with self.assertLogs("dancesport.gui", level="WARNING") as logs:
            _load({"master_volume": "loud"})
        self.assertIn("master_volume", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
