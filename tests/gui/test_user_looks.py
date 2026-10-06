#!/usr/bin/env python3
"""🎨 Looks of your own: kept in looks.json, checked when read, passed on as a file.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_user_looks -v
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_user_looks_"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from shared import looks, theme, user_looks  # noqa: E402


class _Clean(unittest.TestCase):

    def setUp(self):
        self._state = tempfile.mkdtemp(prefix="dp_user_looks_")
        self._env = os.environ.get("DANCEPLAYLIST_STATE_DIR")
        os.environ["DANCEPLAYLIST_STATE_DIR"] = self._state
        user_looks.load()
        self.addCleanup(self._restore)

    def _restore(self):
        os.environ["DANCEPLAYLIST_STATE_DIR"] = self._env
        user_looks.load()
        theme.set_active("light")

    def made(self, source="midnight", name="Hall at night"):
        look = user_looks.copy_of(looks.LOOKS[source], name)
        user_looks.put(look)
        return look


class OwnLookDataTest(_Clean):

    def test_a_copy_keeps_its_source_but_is_yours(self):
        look = user_looks.copy_of(looks.LOOKS["console"], "Mein Pult")
        self.assertEqual(look.key, "own_mein_pult")
        self.assertEqual(look.group, user_looks.GROUP)
        self.assertEqual(looks.family(look), "desk")
        self.assertEqual(look.tokens, looks.LOOKS["console"].tokens)

    def test_a_copy_keeps_the_details_of_its_family(self):
        """A copy of a desk look still draws faders: the sheet is the same."""
        source = looks.LOOKS["console"]
        look = user_looks.copy_of(source, "Pult")
        self.assertEqual(looks.stylesheet(look), looks.stylesheet(source))

    def test_it_survives_a_restart(self):
        look = self.made()
        user_looks.load()
        self.assertEqual(looks.get(look.key), look)

    def test_a_stored_own_look_is_a_theme(self):
        look = self.made()
        self.assertEqual(theme.theme_of({"theme": look.key}), look.key)
        theme.set_active(look.key)
        self.assertIs(theme.active_look(), looks.get(look.key))

    def test_once_removed_the_setting_falls_back_to_light(self):
        look = self.made()
        self.assertTrue(user_looks.remove(look.key))
        user_looks.load()
        self.assertEqual(theme.theme_of({"theme": look.key}), "light")

    def test_a_built_in_look_cannot_be_removed(self):
        self.assertFalse(user_looks.remove("midnight"))
        self.assertIsNotNone(looks.get("midnight"))

    def test_a_second_look_of_the_same_name_gets_its_own_key(self):
        one, two = self.made(name="Gala"), self.made(name="Gala")
        self.assertNotEqual(one.key, two.key)
        self.assertEqual(len(user_looks.mine()), 2)

    def test_dark_follows_the_window_colour(self):
        self.assertTrue(user_looks.is_dark("#101010"))
        self.assertFalse(user_looks.is_dark("#f0f0f0"))
        data = user_looks.to_dict(user_looks.copy_of(looks.LOOKS["paper"], "x"))
        data["tokens"]["window"] = "#111111"
        self.assertTrue(user_looks.from_dict(data).dark)

    def test_a_round_trip_through_the_dict_is_lossless(self):
        look = user_looks.copy_of(looks.LOOKS["studio"], "Daylight")
        self.assertEqual(user_looks.from_dict(user_looks.to_dict(look)), look)


class OwnLookCheckTest(_Clean):

    def entry(self, **change):
        data = user_looks.to_dict(user_looks.copy_of(looks.LOOKS["paper"], "x"))
        tokens = change.pop("tokens", {})
        data.update(change)
        data["tokens"].update(tokens)
        return data

    def test_each_broken_field_is_named(self):
        for change, field in (({"tokens": {"text": "red"}}, "tokens.text"),
                              ({"tokens": {"radius": 99}}, "tokens.radius"),
                              ({"buttons": "round"}, "buttons"),
                              ({"family": "user"}, "family"),
                              ({"key": "midnight"}, "key"),
                              ({"name": " "}, "name"),
                              ({"fonts": []}, "fonts")):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, field):
                    user_looks.from_dict(self.entry(**change))

    def test_a_missing_colour_is_refused_but_a_missing_gradient_is_flat(self):
        data = self.entry()
        del data["tokens"]["header_top"]
        self.assertEqual(user_looks.from_dict(data).tokens.header_top, "")
        del data["tokens"]["base"]
        with self.assertRaisesRegex(ValueError, "tokens.base"):
            user_looks.from_dict(data)

    def test_a_broken_entry_is_left_out_and_the_rest_load(self):
        good = self.entry(key="own_good", name="Good")
        bad = self.entry(key="own_bad", name="Bad", tokens={"base": "nope"})
        user_looks.STORE.write({"version": 1, "looks": [bad, good]})
        with self.assertLogs("dancesport.looks", "WARNING") as logs:
            loaded = user_looks.load()
        self.assertEqual([lk.key for lk in loaded], ["own_good"])
        self.assertIn("tokens.base", logs.output[0])

    def test_an_unreadable_file_leaves_the_built_in_looks(self):
        user_looks.STORE.path.write_text("{ nope", encoding="utf-8")
        with self.assertLogs("dancesport.store", "WARNING"):
            self.assertEqual(user_looks.load(), [])
        self.assertIsNotNone(looks.get("midnight"))


class OwnLookFileTest(_Clean):

    def test_export_then_import_adds_a_numbered_copy(self):
        look = self.made(name="Gala")
        path = Path(self._state) / "gala.json"
        user_looks.export(look, path)
        self.assertEqual(json.loads(path.read_text("utf-8"))["name"], "Gala")
        copy = user_looks.import_file(path)
        self.assertEqual(copy.caption, "Gala (2)")
        self.assertNotEqual(copy.key, look.key)
        self.assertEqual(copy.tokens, look.tokens)

    def test_importing_into_a_fresh_machine_keeps_the_name(self):
        look = self.made(name="Gala")
        path = Path(self._state) / "gala.json"
        user_looks.export(look, path)
        user_looks.remove(look.key)
        self.assertEqual(user_looks.import_file(path).caption, "Gala")

    def test_a_json_that_is_not_a_look_is_refused(self):
        path = Path(self._state) / "other.json"
        path.write_text(json.dumps({"theme": "dark"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not an exported look"):
            user_looks.import_file(path)
        path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not JSON"):
            user_looks.import_file(path)


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    unittest.main()
