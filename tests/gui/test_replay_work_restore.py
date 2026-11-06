#!/usr/bin/env python3
"""A stashed replay grid comes back with its marks, pins and hidden dances.

Run:  py -m unittest tests.gui.test_replay_work_restore -v

`_stash_replay_work` keeps the whole deck snapshot, which carries the 🔁 marks,
the 📌 pins and each round's hidden dances. `_restore_replay_work` rebuilt the
grid from it but handed none of the three to `table.load`, so switching away
from a competition and back lost them.
"""

import os
import tempfile
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_replaywork_"))

from gui.window import main_persist as persist
from planner.models import RoundConfig, RoundTier


def _host():
    h = mock.MagicMock(name="win")
    h._playlist_from_grid.return_value = {}
    h._effective_replay_pools.return_value = None
    h._replay_work = {}
    h._restore_replay_work = types.MethodType(
        persist.PersistenceMixin._restore_replay_work, h)
    return h


class RestoreReplayWorkTest(unittest.TestCase):

    def work(self, **grid_extra):
        grid = {"mode": "Favorites", "rounds": [], **grid_extra}
        return {
            "grid": grid, "rounds": [RoundConfig(name="Final", heats=1, tier=RoundTier.of(None))],
            "pools": None, "use_timbre": True, "label": "X",
            "dances": ["Samba", "Cha Cha"], "dance_class": "S",
            "style": "Latin", "age": "Adult",
        }

    def loaded(self, h):
        return h._deckset.table.load.call_args.kwargs

    def test_marks_and_pins_come_back(self):
        h = _host()
        h._replay_work[0] = self.work(marked=["a.mp3"], pinned=["b.mp3"])
        h._restore_replay_work(0)
        kw = self.loaded(h)
        self.assertEqual(kw["marked"], {"a.mp3"})
        self.assertEqual(kw["pinned"], {"b.mp3"})

    def test_hidden_dances_come_back(self):
        h = _host()
        work = self.work()
        work["grid"]["rounds"] = [{"name": "Final", "skip_dances": ["Samba"]}]
        h._replay_work[0] = work
        h._restore_replay_work(0)
        self.assertEqual(self.loaded(h)["round_skip_dances"],
                         {"Final": {"Samba"}})

    def test_a_grid_without_any_of_them_loads_clean(self):
        h = _host()
        h._replay_work[0] = self.work()
        h._restore_replay_work(0)
        kw = self.loaded(h)
        self.assertEqual(kw["marked"], set())
        self.assertEqual(kw["pinned"], set())
        self.assertEqual(kw["round_skip_dances"], {})


if __name__ == "__main__":
    unittest.main()
