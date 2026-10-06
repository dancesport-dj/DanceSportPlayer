#!/usr/bin/env python3
"""Tests for tools/build_manual_pdf.py — which browser prints, and how.

Run:  py -m unittest tests.app.test_build_manual_pdf -v

The browser itself never runs here: subprocess.run is replaced by a fake
that writes (or does not write) the PDF.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse
from urllib.request import url2pathname

from tools import build_manual_html as bm
from tools import build_manual_pdf as bp


# What Chrome writes, cut down: the catalog's /Dests maps every anchor to its
# page object, and the page tree nests. Names escape non-ASCII bytes as #xx,
# and Chrome percent-encodes the anchor first, so an umlaut comes as #25C3#25B6.
PDF_WITH_DESTS = b"""%PDF-1.7
1 0 obj
<</Type /Catalog
/Pages 2 0 R
/Dests 3 0 R>>
endobj
2 0 obj
<</Type /Pages
/Count 3
/Kids [4 0 R 7 0 R]>>
endobj
3 0 obj
<</01-start [6 0 R /XYZ 0 792 0]
/01-start__f#C3#BCr [6 0 R /XYZ 0 300 0]
/01-start__#25C3#25B6ffnen [7 0 R /XYZ 0 500 0]
/index [5 0 R /XYZ 0 792 0]>>
endobj
4 0 obj
<</Type /Pages
/Kids [5 0 R 6 0 R]>>
endobj
5 0 obj
<</Type /Page
/Parent 4 0 R>>
endobj
6 0 obj
<</Type /Page>>
endobj
7 0 obj
<</Type /Page>>
endobj
"""


class BuildManualPdfTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "README.md").write_text(
            "# The Player Manual\n\n1. [Start](01-start.md)\n", encoding="utf-8")
        (self.dir / "01-start.md").write_text(
            "# 1 · Start\n\nHello.\n", encoding="utf-8")
        self.pdf = self.dir / "manual.pdf"

    def test_the_browser_named_in_the_environment_wins(self):
        with mock.patch.dict(os.environ, {bp.BROWSER_ENV: "/opt/my/chrome"}):
            self.assertEqual(bp.findBrowser(), "/opt/my/chrome")

    def test_the_print_has_no_browser_header_or_footer(self):
        # The footer would print the file's path, the build machine's user folder in it.
        cmd = bp.printCommand("chrome", self.dir / "manual.html", self.pdf, self.dir / "p")
        self.assertIn("--no-pdf-header-footer", cmd)
        self.assertIn(f"--user-data-dir={self.dir / 'p'}", cmd)
        self.assertEqual(cmd[-1], (self.dir / "manual.html").as_uri())

    def test_the_pdf_gets_bookmarks_from_the_headings(self):
        cmd = bp.printCommand("chrome", self.dir / "manual.html", self.pdf, self.dir / "p")
        self.assertIn("--generate-pdf-document-outline", cmd)

    def lastPdf(self, age):
        """A PDF from an earlier build, `age` seconds older than the chapters."""
        self.pdf.write_bytes(b"last")
        when = (self.dir / "01-start.md").stat().st_mtime - age
        os.utime(self.pdf, (when, when))

    def fakeBrowser(self, writes):
        def run(cmd, **kwargs):
            out = next(a for a in cmd if a.startswith("--print-to-pdf="))
            if writes:
                Path(out.split("=", 1)[1]).write_bytes(b"%PDF-1.7")
            return mock.Mock(returncode=0, stderr="")
        return run

    def test_the_html_is_built_and_printed_to_the_pdf(self):
        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(True)), \
                self.assertLogs(bm.log, "INFO"):
            code = bp.buildPdf(self.dir, self.pdf)
        self.assertEqual(code, 0)
        self.assertTrue((self.dir / "manual.html").is_file())
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.7")

    def test_no_pdf_written_is_a_failure(self):
        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(False)), \
                self.assertLogs(bm.log, "INFO") as logs:
            code = bp.buildPdf(self.dir, self.pdf)
        self.assertEqual(code, 1)
        self.assertIn("wrote no PDF", "\n".join(logs.output))

    def test_a_failed_print_keeps_the_last_pdf_and_still_fails(self):
        # The ARM Linux runner has no browser and brings the PDF from CI's
        # manual job; the script's own try must not delete it.
        self.lastPdf(60)
        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(False)), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bp.buildPdf(self.dir, self.pdf), 1)
        self.assertEqual(self.pdf.read_bytes(), b"last")
        self.assertEqual([p.name for p in self.dir.glob("*.pdf")], ["manual.pdf"])

    def test_a_good_print_replaces_the_last_pdf(self):
        self.lastPdf(60)
        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(True)), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bp.buildPdf(self.dir, self.pdf), 0)
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.7")

    def test_an_up_to_date_pdf_is_kept_without_printing(self):
        # CI prints once in its manual job; the build scripts then find that
        # PDF newer than every chapter and copy it instead of printing again.
        self.lastPdf(-60)
        with mock.patch.object(bp, "findBrowser", side_effect=AssertionError("printed")), \
                self.assertLogs(bm.log, "INFO") as logs:
            self.assertEqual(bp.buildPdf(self.dir, self.pdf), 0)
        self.assertEqual(self.pdf.read_bytes(), b"last")
        self.assertIn("up to date", "\n".join(logs.output))

    def test_a_chapter_newer_than_the_pdf_prints_it_again(self):
        self.lastPdf(60)
        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(True)), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bp.buildPdf(self.dir, self.pdf), 0)
        self.assertEqual(self.pdf.read_bytes(), b"%PDF-1.7")

    def test_no_browser_is_a_failure(self):
        with mock.patch.object(bp, "findBrowser", return_value=None), \
                self.assertLogs(bm.log, "INFO") as logs:
            code = bp.buildPdf(self.dir, self.pdf)
        self.assertEqual(code, 1)
        self.assertIn(bp.BROWSER_ENV, "\n".join(logs.output))

    def test_without_a_folder_both_languages_are_printed(self):
        de = self.dir / "de"
        de.mkdir()
        for md in ("README.md", "01-start.md"):
            (de / md).write_text((self.dir / md).read_text(encoding="utf-8"), encoding="utf-8")
        with mock.patch.object(bm, "MANUALS", (self.dir, de)), \
                mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", self.fakeBrowser(True)), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bp.main([]), 0)
        self.assertTrue(self.pdf.is_file())
        self.assertTrue((de / "manual.pdf").is_file())

    def test_page_numbers_come_from_the_pdfs_named_destinations(self):
        self.assertEqual(bp.destPages(PDF_WITH_DESTS),
                         {"index": 1, "01-start": 2, "01-start__für": 2,
                          "01-start__öffnen": 3})

    def test_a_pdf_without_destinations_has_no_page_numbers(self):
        self.assertEqual(bp.destPages(b"%PDF-1.7"), {})

    def test_the_second_print_carries_the_page_numbers_of_the_first(self):
        printed = []

        def run(cmd, **kwargs):
            page = url2pathname(urlparse(cmd[-1]).path)
            printed.append(Path(page).read_text(encoding="utf-8"))
            out = next(a for a in cmd if a.startswith("--print-to-pdf="))
            Path(out.split("=", 1)[1]).write_bytes(PDF_WITH_DESTS)
            return mock.Mock(returncode=0, stderr="")

        with mock.patch.object(bp, "findBrowser", return_value="chrome"), \
                mock.patch.object(bp.subprocess, "run", run), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bp.buildPdf(self.dir, self.pdf), 0)
        self.assertEqual(len(printed), 2)
        self.assertIn('<span class="pg"></span>', printed[0])
        self.assertIn('<a href="#01-start"><span class="label">1 · Start</span>'
                      '<span class="dots"></span><span class="pg">2</span>', printed[1])
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()),
                         ["01-start.md", "README.md", "manual.html", "manual.pdf"])

    def test_the_print_hides_the_index_button_and_starts_chapters_on_a_page(self):
        page, _ = bm.buildHtml(self.dir)
        css = page.split("@media print", 1)[1]
        self.assertIn(".top { display:none; }", css)
        self.assertIn("section { break-before:page;", css)


if __name__ == "__main__":
    unittest.main()
