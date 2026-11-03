"""A non-string path in the path config must not stop the app at import (review item 2)."""
import unittest
from pathlib import Path
from unittest import mock

from planner import config


class ConfiguredDirTests(unittest.TestCase):
    def dirOf(self, value):
        with mock.patch.dict(config._PATH_CFG, {"x_dir": value}), \
                mock.patch.dict("os.environ", {}, clear=False):
            return config._configured_dir("DANCEPLAYLIST_TEST_UNSET", "x_dir", Path("dflt"))

    def test_non_string_values_fall_back(self):
        for value in (5, 1.5, ["a"], {"a": 1}, True):
            with self.subTest(value=value):
                self.assertEqual(self.dirOf(value), Path("dflt"))

    def test_string_still_works(self):
        self.assertEqual(self.dirOf("somewhere"), Path("somewhere"))

    def test_blank_string_falls_back(self):
        self.assertEqual(self.dirOf("  "), Path("dflt"))


if __name__ == "__main__":
    unittest.main()
