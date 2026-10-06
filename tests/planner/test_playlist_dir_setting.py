#!/usr/bin/env python3
"""planner.config.set_playlist_dir — the ⚙ playlist-folder setting.

Run:  py -m unittest tests.planner.test_playlist_dir_setting -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

from planner import config as planner_config
from planner import event_plan  # noqa: F401  (imported at GUI start, before the setting)


class SetPlaylistDirTest(unittest.TestCase):
    def test_every_module_holding_the_name_follows(self):
        """The modules import PLAYLIST_DIR by name, and the GUI loads them before
        it applies the setting. planner.event_plan was missed, so the search
        for an event's past editions looked in the default folder."""
        orig = planner_config.PLAYLIST_DIR
        self.addCleanup(planner_config.set_playlist_dir, orig)
        folder = Path(tempfile.gettempdir()) / "dp_setting_target"
        planner_config.set_playlist_dir(folder)
        holders = {name: mod.PLAYLIST_DIR for name, mod in list(sys.modules.items())
                   if (name.startswith("planner.") or name == "dancesport_planner")
                   and hasattr(mod, "PLAYLIST_DIR")}
        self.assertIn("planner.event_plan", holders)
        self.assertEqual({n: d for n, d in holders.items() if d != folder}, {})


if __name__ == "__main__":
    unittest.main()
