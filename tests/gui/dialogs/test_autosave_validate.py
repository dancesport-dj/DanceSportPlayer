"""🗂️ An autosave part of the wrong container type is dropped, not trusted (#28)."""
import unittest
from unittest import mock

import gui.dialogs as dialogs
from gui.dialogs import validate_env


class ValidateEnvTest(unittest.TestCase):

    def test_wrong_containers_are_dropped_and_named(self):
        data = {"version": 3, "names": ["x"], "deck_a": "oops", "wishlist": {"a": 1},
                "m3u_paths": {"deck_a": "a.m3u"}, "wishlist2": ["p.mp3"]}
        self.assertEqual(sorted(validate_env(data)), ["deck_a", "names", "wishlist"])
        self.assertEqual(data, {"version": 3, "m3u_paths": {"deck_a": "a.m3u"},
                                "wishlist2": ["p.mp3"]})

    def test_a_good_file_is_untouched(self):
        data = {"version": 3, "names": {}, "deck_a": {}, "wishlist": []}
        self.assertEqual(validate_env(data), [])

    def test_an_empty_deck_saved_as_null_is_no_warning(self):
        # The writer stores a deck with no playlist as null (serialize_deck).
        data = {"version": 4, "deck_a": None, "deck_b": {}, "names": {}}
        with self.assertNoLogs(level="WARNING"):
            self.assertEqual(dialogs.validate_env(data), [])
            with mock.patch.object(dialogs.AUTOSAVE, "read", return_value=dict(data)):
                loaded = dialogs.load_autosave()
        self.assertNotIn("deck_a", loaded)

    def test_load_autosave_applies_it(self):
        with mock.patch.object(dialogs.AUTOSAVE, "read",
                               return_value={"version": 3, "names": 5, "deck_a": {}}):
            self.assertEqual(dialogs.load_autosave(), {"version": 3, "deck_a": {}})


if __name__ == "__main__":
    unittest.main()
