#!/usr/bin/env python3
"""Tests for tools/build_manual_html.py — which manual it builds, and its title.

Run:  py -m unittest tests.app.test_build_manual_html -v

There are two manuals: the player's in docs/manual (public) and the
planner's, kept on this machine only. The builder takes either folder and
names the page after that manual's own index heading.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import build_manual_html as bm


class BuildManualTest(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "README.md").write_text(
            "# The Player Manual\n\n1. [Start](01-start.md)\n", encoding="utf-8")
        (self.dir / "01-start.md").write_text(
            "# 1 · Start\n\nHello.\n", encoding="utf-8")

    def test_the_page_is_named_after_the_index_heading(self):
        page, broken = bm.buildHtml(self.dir)
        self.assertIn("<title>The Player Manual</title>", page)
        self.assertEqual(broken, [])

    def test_a_folder_given_is_built_into_its_own_manual_html(self):
        with self.assertLogs(bm.log, "INFO"):
            code = bm.main([str(self.dir)])
        self.assertEqual(code, 0)
        self.assertIn("Hello.", (self.dir / "manual.html").read_text(encoding="utf-8"))


class PrintManualTest(unittest.TestCase):
    """The page the PDF is printed from: a cover, a contents page with page
    numbers, then the chapters without the web page's navigation."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        (self.dir / "README.md").write_text(
            "# DanceSport Player — User Manual\n\nAn intro.\n\n"
            "The whole manual is also a single web page, [manual.html](manual.html).\n\n"
            "## Chapters\n\n1. [Start](01-start.md)\n", encoding="utf-8")
        (self.dir / "01-start.md").write_text(
            "# 1 · Start\n\n[Manual index](README.md)\n\nHello.\n\n"
            "## First steps\n\nSee [the index](README.md) for every chapter there is.\n\n"
            "Back to the [manual index](README.md).\n", encoding="utf-8")

    def test_the_cover_names_the_app_the_manual_and_the_version(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        cover = page.split('<div class="cover">', 1)[1].split("</div>", 1)[0]
        self.assertIn('<p class="product">DanceSport Player</p>', cover)
        self.assertIn('<p class="kind">User Manual</p>', cover)
        self.assertIn('<p class="version">Version 1.2.3</p>', cover)

    def test_the_contents_lists_chapters_and_sections_with_their_pages(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3",
                                 {"index": 3, "01-start": 5, "01-start__first-steps": 6})
        contents = page.split('<nav class="contents">', 1)[1].split("</nav>", 1)[0]
        self.assertIn('<a href="#01-start"><span class="label">1 · Start</span>'
                      '<span class="dots"></span><span class="pg">5</span></a>', contents)
        self.assertIn('<span class="label">First steps</span>'
                      '<span class="dots"></span><span class="pg">6</span>', contents)
        self.assertIn('<span class="label">Overview</span>', contents)

    def test_without_pages_the_contents_leaves_the_numbers_blank(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        self.assertIn('<span class="pg"></span>', page)

    def test_the_print_has_no_web_navigation(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        self.assertNotIn('class="toc"', page)
        self.assertNotIn("↑ Index", page)
        self.assertNotIn("<script>", page)
        self.assertNotIn("manual.html", page)
        self.assertNotIn("Manual index", page)
        self.assertNotIn("Back to the", page)
        self.assertIn("for every chapter there is", page)
        self.assertIn("An intro.", page)

    def test_the_index_chapter_is_the_overview_in_print(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        self.assertIn('<section id="index">\n<h1>Overview</h1>', page)

    def test_the_web_page_is_english(self):
        page, _ = bm.buildHtml(self.dir)
        self.assertIn('<html lang="en">', page)
        self.assertIn('<p class="title">User Manual</p>', page)

    def test_screenshots_fit_a_page_and_stay_with_the_text_before_them(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        css = page.split("@media print", 1)[1]
        self.assertIn("max-height:", css.split("figure img", 1)[1].split("}", 1)[0])
        self.assertIn("p:has(+ figure)", css)


class GermanManualTest(unittest.TestCase):
    """The German translation lives in a folder named "de" and shares the
    English screenshots in ../img; the builder's own words follow it."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name) / "de"
        self.dir.mkdir()
        (self.dir.parent / "img").mkdir()
        (self.dir.parent / "img" / "shot.png").write_bytes(b"png")
        (self.dir / "README.md").write_text(
            "# DanceSport Player — Benutzerhandbuch\n\nEine Einleitung.\n\n"
            "Das ganze Handbuch gibt es auch als eine einzige Webseite,\n"
            "[manual.html](manual.html).\n\n"
            "![Ein Bild](../img/shot.png)\n\n"
            "## Kapitel\n\n1. [Start](01-start.md)\n", encoding="utf-8")
        (self.dir / "01-start.md").write_text(
            "# 1 · Start\n\n[Zurück zur Übersicht](README.md)\n\nHallo.\n\n"
            "## Für den Anfang\n\nSiehe [die Übersicht](README.md), dort steht jedes Kapitel.\n\n"
            "Zurück zur [Übersicht](README.md).\n", encoding="utf-8")

    def test_the_web_page_is_german(self):
        page, broken = bm.buildHtml(self.dir)
        self.assertIn('<html lang="de">', page)
        self.assertIn('<p class="title">Benutzerhandbuch</p>', page)
        self.assertIn('<a href="#index">Übersicht</a>', page)
        self.assertIn("↑ Übersicht", page)
        self.assertIn('href="#01-start__für-den-anfang"', page)
        self.assertEqual(broken, [])

    def test_the_shared_screenshots_are_found(self):
        with self.assertLogs(bm.log, "INFO") as logs:
            self.assertEqual(bm.main([str(self.dir)]), 0)
        self.assertNotIn("Missing image", "\n".join(logs.output))

    def test_the_print_is_german(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        self.assertIn('<html lang="de">', page)
        self.assertIn('<p class="kind">Benutzerhandbuch</p>', page)
        self.assertIn('<p class="version">Version 1.2.3</p>', page)
        self.assertIn('<nav class="contents"><h1>Inhalt</h1>', page)
        self.assertIn('<section id="index">\n<h1>Übersicht</h1>', page)

    def test_the_print_drops_the_german_web_navigation(self):
        page = bm.buildPrintHtml(self.dir, "1.2.3")
        self.assertNotIn("manual.html", page)
        self.assertNotIn("Zurück zur", page)
        self.assertIn("dort steht jedes Kapitel", page)

    def test_without_a_folder_both_languages_are_built(self):
        en = Path(self.dir.parent) / "en"
        en.mkdir()
        (en / "README.md").write_text("# Manual\n\nHi.\n", encoding="utf-8")
        with mock.patch.object(bm, "MANUALS", (en, self.dir)), \
                self.assertLogs(bm.log, "INFO"):
            self.assertEqual(bm.main([]), 0)
        self.assertTrue((en / "manual.html").is_file())
        self.assertTrue((self.dir / "manual.html").is_file())


if __name__ == "__main__":
    unittest.main()
