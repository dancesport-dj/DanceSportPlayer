#!/usr/bin/env python3
"""One file that cannot be read does not stop the Custom field's re-read.

Run:  py -m unittest tests.gui.test_custom_field_reader -v

`CustomFieldReader.run` had no guard: a read that raised killed the thread
before `done` was emitted, so the window's `_custom_reader` was never cleared
and the Custom field could not be mapped again until a restart.
"""

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from gui import workers

GOOD = r"C:\music\tanzcds\standardcd\TG\Tanguera (TG 32).mp3"
BAD = r"C:\music\tanzcds\standardcd\TG\Broken (TG 32).mp3"


def _read_file(path):
    if path == BAD:
        raise UnicodeDecodeError("latin-1", b"\xff", 0, 1, "a mangled frame")
    return "Klassiker"


class CustomFieldReaderTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_a_file_that_raises_reads_as_empty_and_the_rest_still_arrive(self):
        reader = workers.CustomFieldReader([GOOD, BAD])
        self.addCleanup(reader.deleteLater)
        got = []
        reader.done.connect(got.append)

        with mock.patch.object(workers.custom_field, "read_file", _read_file):
            reader.run()

        self.assertEqual(got, [{GOOD: "Klassiker", BAD: ""}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
