#!/usr/bin/env python3
"""🖨 Printing a playlist twice on one day must not lose the first PDF.

The file is named <date>_<name>.pdf, so the second print writes to the same
path. QPdfWriter truncates it the moment it is constructed: a write that failed
after that left a cut-off PDF where a whole one had been.
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QApplication, QMessageBox

from gui.window import main_print


class _Host:
    """What _write_print_pdf asks of the window."""

    def __init__(self):
        self.shown = []

    def statusBar(self):
        host = self

        class _Bar:
            def showMessage(self, text, *_):
                host.shown.append(text)

        return _Bar()


def _write(host, parts, name="Party"):
    main_print.PrintMixin._write_print_pdf(host, parts, name)


class PrintPdfOverwriteTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_print_"))
        self.addCleanup(shutil.rmtree, self.dir, True)
        for patch in (mock.patch.object(main_print, "OUTPUT_DIR", self.dir),
                      mock.patch.object(QMessageBox, "question",
                                        return_value=QMessageBox.StandardButton.No),
                      mock.patch.object(QMessageBox, "critical")):
            patch.start()
            self.addCleanup(patch.stop)
        self.host = _Host()

    def _pdfs(self):
        return sorted(self.dir.iterdir())

    def test_a_print_makes_a_whole_pdf_and_leaves_nothing_else(self):
        _write(self.host, ["<h1>One</h1><p>Moon River</p>"])
        [pdf] = self._pdfs()
        self.assertEqual(pdf.suffix, ".pdf")
        data = pdf.read_bytes()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertIn(b"%%EOF", data[-64:])

    def test_a_second_print_replaces_the_first_whole(self):
        _write(self.host, ["<p>first</p>"])
        [pdf] = self._pdfs()
        first = pdf.read_bytes()
        _write(self.host, ["<p>second, a longer text</p>" * 40])
        [pdf] = self._pdfs()
        self.assertNotEqual(pdf.read_bytes(), first)
        self.assertIn(b"%%EOF", pdf.read_bytes()[-64:])

    def test_a_write_that_fails_keeps_the_first_pdf(self):
        _write(self.host, ["<p>first</p>"])
        [pdf] = self._pdfs()
        first = pdf.read_bytes()

        def dies_after_the_file_is_opened(_doc, writer):
            # QPdfWriter opens (and so empties) its file when painting begins.
            QPainter(writer).end()
            raise OSError("disk full")

        with mock.patch.object(main_print.QTextDocument, "print_",
                               dies_after_the_file_is_opened):
            _write(self.host, ["<p>second</p>"])
        self.assertEqual(self._pdfs(), [pdf])
        self.assertEqual(pdf.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
