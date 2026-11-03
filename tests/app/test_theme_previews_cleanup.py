"""🧹 theme_previews leaves no state directory behind and rejects a bare --one (#80)."""
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tools.assets import theme_previews as tp


class CleanupTest(unittest.TestCase):

    def test_each_render_state_dir_is_removed_by_the_parent(self):
        seen = []

        def fake_run(cmd, cwd=None, env=None):
            state = Path(env["DANCEPLAYLIST_STATE_DIR"])
            self.assertTrue(state.is_dir())
            seen.append(state)
            return subprocess.CompletedProcess(cmd, 0)

        with mock.patch.object(tp.subprocess, "run", side_effect=fake_run):
            self.assertEqual(tp.main(["light", "dark"]), 0)
        self.assertEqual(len(seen), 2)
        self.assertEqual(len(set(seen)), 2)
        self.assertFalse(any(p.exists() for p in seen))

    def test_a_render_without_a_key_is_refused(self):
        self.assertEqual(tp.main(["--one"]), 2)


if __name__ == "__main__":
    unittest.main()
