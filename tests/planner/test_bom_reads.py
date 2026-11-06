"""A JSON file saved with a UTF-8 BOM (PowerShell 5.1 `Set-Content -Encoding utf8`,
Notepad) must read like any other: the config and store reads used `utf-8`, so
json.loads choked on the BOM and the settings silently reverted. Review 2026-11-06."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from planner import config
from planner.store import JsonStore
from shared.appearance import user_looks


def _bomFile(directory: str, name: str, text: str) -> Path:
    path = Path(directory) / name
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
    return path


class BomReadsTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="dp_bom_")
        self.addCleanup(self.tmp.cleanup)

    def test_the_path_config_reads_with_a_bom(self):
        path = _bomFile(self.tmp.name, "planner_config.json", json.dumps({"a": 1}))
        with mock.patch.object(config, "PATH_CONFIG_FILE", path):
            self.assertEqual(config._load_path_config(), {"a": 1})

    def test_a_json_store_reads_with_a_bom(self):
        _bomFile(self.tmp.name, "thing.json", json.dumps({"k": 2}))
        store = JsonStore("thing.json", root=lambda: Path(self.tmp.name))
        self.assertEqual(store.read({}), {"k": 2})

    def test_an_exported_look_with_a_bom_is_parsed_as_json(self):
        path = _bomFile(self.tmp.name, "look.json", "{}")
        with self.assertRaises(ValueError) as ctx:
            user_looks.import_file(path)
        self.assertNotIn("not JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
