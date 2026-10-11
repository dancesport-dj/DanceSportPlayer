#!/usr/bin/env python3
"""planner.config.set_playlist_dir — the ⚙ playlist-folder setting.

Run:  py -m unittest tests.planner.test_playlist_dir_setting -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

import dancesport_planner  # noqa: F401  (the facade, loaded by the CLI)
from planner import config as planner_config
from planner import competition, event_plan, library  # noqa: F401  (imported at GUI start, before the setting)


class SetPlaylistDirTest(unittest.TestCase):
    def setUp(self):
        orig = planner_config.playlist_dir()
        self.addCleanup(planner_config.set_playlist_dir, orig)
        self.folder = Path(tempfile.gettempdir()) / "dp_setting_target"
        planner_config.set_playlist_dir(self.folder)

    def test_the_accessor_follows(self):
        self.assertEqual(planner_config.playlist_dir(), self.folder)

    def test_no_module_keeps_a_copy(self):
        """The modules imported PLAYLIST_DIR by name, and the GUI loads them
        before it applies the setting, so set_playlist_dir patched four named
        modules by hand. planner.event_plan was once missed, and the search for
        an event's past editions looked in the default folder. Now they read
        config.playlist_dir() at call time and hold no copy to go stale."""
        holders = sorted(name for name, mod in list(sys.modules.items())
                         if (name.startswith("planner.") or name == "dancesport_planner")
                         and name != "planner.config"
                         and hasattr(mod, "PLAYLIST_DIR"))
        self.assertEqual(holders, [])

    def test_the_superseded_check_reads_the_new_folder(self):
        # Relative to the new folder, "alt" is an old-version segment.
        self.assertTrue(competition._is_superseded_playlist(
            self.folder / "2020" / "alt" / "x.m3u"))


if __name__ == "__main__":
    unittest.main()
