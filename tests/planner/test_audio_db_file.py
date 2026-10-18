"""planner.config.audio_db_file() — the one place the DB path is read from.

Run:  py -m unittest tests.planner.test_audio_db_file -v

planner.music.db imported AUDIO_DB_FILE by name, so a test that wanted a scratch DB
had to patch planner.music.db's copy; patching config did nothing. db now reads
config.audio_db_file() when it opens a connection, and the tests set
planner.config.AUDIO_DB_FILE. A test still assigning another module's copy
would quietly open the suite's shared DB, so the source scan below refuses it.
"""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import dancesport_planner  # noqa: F401  (the facade, loaded by the CLI)
import planner.music.db as pdb
from planner import config as planner_config
from tests.db_support import use_scratch_db

_TESTS = Path(__file__).resolve().parents[1]


class AudioDbFileTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_db_file_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        use_scratch_db(self, self.dir / "scratch.db")

    def test_the_accessor_follows_config(self):
        self.assertEqual(planner_config.audio_db_file(), self.dir / "scratch.db")

    def test_db_opens_the_file_config_names(self):
        pdb._db()
        self.assertTrue((self.dir / "scratch.db").exists())

    def test_no_planner_module_keeps_a_copy(self):
        import sys
        holders = sorted(name for name, mod in list(sys.modules.items())
                         if (name.startswith("planner.") or name == "dancesport_planner")
                         and name != "planner.config"
                         and "AUDIO_DB_FILE" in vars(mod))
        self.assertEqual(holders, [])

    def test_no_test_patches_another_modules_copy(self):
        stale = re.compile(r"\b(?!planner_config\b|config\b)\w+\.AUDIO_DB_FILE\b")
        hits = [f"{p.relative_to(_TESTS)}:{n}"
                for p in sorted(_TESTS.rglob("*.py")) if p.name != Path(__file__).name
                for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
                if stale.search(line)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
