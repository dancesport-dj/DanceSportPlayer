#!/usr/bin/env python3
"""The printed playlist PDF opens when asked to.

Run:  .venv\\Scripts\\python.exe -m unittest tests.gui.test_print_open_pdf -v

The "Open it now?" answer went through _open_in_default_player, whose audio
allowlist refuses every other suffix, so the PDF just written was answered with
"This is not an audio file, so it won't be opened".
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from gui import common
from gui.window import main_print


class PrintOpenPdfTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_yes_opens_the_written_pdf(self):
        window = mock.MagicMock()
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(main_print, "OUTPUT_DIR", Path(tmp)), \
                mock.patch.object(main_print.QMessageBox, "question",
                                  return_value=QMessageBox.StandardButton.Yes), \
                mock.patch.object(common, "QMessageBox") as box, \
                mock.patch.object(common.os, "startfile", create=True) as startfile, \
                mock.patch.object(common.subprocess, "Popen") as popen:
            main_print.PrintMixin._write_print_pdf(window, ["<p>Waltz</p>"], "Final")
            pdfs = list(Path(tmp).glob("*.pdf"))
        self.assertEqual(len(pdfs), 1)
        box.warning.assert_not_called()
        launched = [str(c.args[0]) for c in startfile.call_args_list] + \
                   [str(c.args[0][-1]) for c in popen.call_args_list]
        self.assertEqual(launched, [str(pdfs[0])])


if __name__ == "__main__":
    unittest.main(verbosity=2)
