#!/usr/bin/env python3
"""Tests for the store the app remembers things in.

Run:  py -m unittest tests.app.test_json_store -v

No Qt: a store is a file name, a folder and the four things that can happen to
it, so the rules are tested without a window. What is pinned here is what the
seven hand-rolled copies used to each promise separately — a missing file is
not an error, an unreadable one costs its content and nothing else, a write
either lands whole or leaves the old one, and none of it ever raises at the
caller. Plus the one they all got wrong: the folder is decided when the file is
read, not when the module is imported.
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from planner import store as planner_store
from planner.store import JsonStore, state_dir


class _StoreCase(unittest.TestCase):
    """A store over its own temp folder, per test."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_store_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.store = JsonStore.at(self.dir / "thing.json")


class ReadTest(_StoreCase):
    def test_nothing_written_yet_is_the_default(self):
        self.assertIsNone(self.store.read())
        self.assertEqual(self.store.read({"a": 1}), {"a": 1})
        self.assertFalse(self.store.exists())

    def test_what_was_written_comes_back(self):
        self.store.write({"a": [1, "zwei"]})
        self.assertEqual(self.store.read(), {"a": [1, "zwei"]})
        self.assertTrue(self.store.exists())

    def test_an_unreadable_file_costs_its_content_and_nothing_else(self):
        self.store.path.write_text("{not json", encoding="utf-8")
        with self.assertLogs("dancesport.store", "WARNING") as caught:
            self.assertEqual(self.store.read([]), [])
        self.assertIn("thing.json", "\n".join(caught.output))

    def _kept(self):
        return sorted(p for p in self.dir.iterdir() if p.name != "thing.json")

    def test_an_unreadable_file_is_kept_before_the_next_write_replaces_it(self):
        """The app carries on with defaults and saves them over the file on the
        next click — a hand edit with one comma wrong cost a whole tournament
        tree, with nothing left to fix the comma in."""
        self.store.path.write_text('{"a": 1,}', encoding="utf-8")
        with self.assertLogs("dancesport.store", "WARNING"):
            self.store.read()
        self.store.write({})
        [kept] = self._kept()
        self.assertEqual(kept.read_text(encoding="utf-8"), '{"a": 1,}')
        self.assertEqual(kept.suffix, ".json")

    def test_a_second_unreadable_file_does_not_replace_the_first_kept_one(self):
        for text in ("{one", "{two"):
            self.store.path.write_text(text, encoding="utf-8")
            with self.assertLogs("dancesport.store", "WARNING"):
                self.store.read()
        self.assertEqual(sorted(p.read_text(encoding="utf-8") for p in self._kept()),
                         ["{one", "{two"])

    def test_umlauts_survive_the_round_trip(self):
        """The files hold dance titles — cp1252 is not an option."""
        self.store.write({"name": "Fürstenball – Grüße"})
        self.assertEqual(self.store.read()["name"], "Fürstenball – Grüße")


class WriteTest(_StoreCase):
    def test_a_write_that_cannot_land_says_so_instead_of_raising(self):
        gone = JsonStore.at(self.dir / "nope" / "thing.json")
        with self.assertLogs("dancesport.store", "ERROR"):
            self.assertFalse(gone.write({"a": 1}))

    def test_the_old_content_survives_a_write_that_fails(self):
        self.store.write({"a": 1})
        with self.assertLogs("dancesport.store", "ERROR"):
            self.assertFalse(self.store.write(object()))   # not JSON
        self.assertEqual(self.store.read(), {"a": 1})

    def test_it_leaves_no_temp_file_behind(self):
        self.store.write({"a": 1})
        self.assertEqual([p.name for p in self.dir.iterdir()], ["thing.json"])

    def test_the_file_is_meant_to_be_hand_editable(self):
        self.store.write({"a": 1})
        self.assertIn("\n", self.store.path.read_text(encoding="utf-8"))


class RemoveTest(_StoreCase):
    def test_forgetting_it_twice_is_not_an_error(self):
        self.store.write({"a": 1})
        self.store.remove()
        self.store.remove()
        self.assertFalse(self.store.exists())
        self.assertIsNone(self.store.read())


class RootTest(unittest.TestCase):
    """Where a store's file lives — decided when it is asked, not at import."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_root_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        self._orig = os.environ.get("DANCEPLAYLIST_STATE_DIR")
        self.addCleanup(self._restore)

    def _restore(self):
        if self._orig is None:
            os.environ.pop("DANCEPLAYLIST_STATE_DIR", None)
        else:
            os.environ["DANCEPLAYLIST_STATE_DIR"] = self._orig

    def test_a_store_follows_a_redirect_set_after_it_was_built(self):
        """The trap the module-level Paths fell into: a test that imported a
        gui module before setting the variable wrote over the real settings."""
        store = JsonStore("gui_settings.json")
        os.environ["DANCEPLAYLIST_STATE_DIR"] = str(self.dir)
        self.assertEqual(store.path.parent, self.dir)
        store.write({"library_dir": "X:\\nowhere"})
        self.assertEqual(
            json.loads((self.dir / "gui_settings.json").read_text(encoding="utf-8")),
            {"library_dir": "X:\\nowhere"})

    def test_the_redirect_folder_is_made_if_it_is_not_there(self):
        nested = self.dir / "a" / "b"
        os.environ["DANCEPLAYLIST_STATE_DIR"] = str(nested)
        self.assertTrue(state_dir().is_dir())

    def test_without_a_redirect_the_state_sits_with_the_app(self):
        os.environ.pop("DANCEPLAYLIST_STATE_DIR", None)
        self.assertEqual(state_dir(), planner_store.config.APP_DIR)


if __name__ == "__main__":
    unittest.main()
