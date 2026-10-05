#!/usr/bin/env python3
"""The left panel's library-status block speaks German.

Run:  py -m unittest tests.gui.test_library_status_i18n -v

This block is not a catalog gap. Every line of it is assembled with an
f-string before it reaches a widget:

    status = f"{self._mode_line()}\\nLibrary: {n} files\\nFavorites: {comp}"

so by the time `ConfigPanel.set_library_status` calls the patched `setText`,
the text is one unique string that matches no catalog key and never will —
the numbers in it change on every refresh. The hook cannot help here; each
fragment has to ask for its own translation and take its numbers through a
placeholder, the way gui/main_wish.py:331 already does it.

The numbers are the reason to be careful: `mark_index_gaps` finds the
"analyzed/total" pairs with a regex and paints a short count amber. A
translation that reshaped those pairs would silently turn that off, so the
German block is run through `mark_index_gaps` here too.

The harness borrows the real unbound methods off GlobalIndexMixin (the same
trick as tests/gui/test_index_gap_flag.py) — a re-implementation of the
assembly would pass while the app stayed English.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_libstatus_i18n_"))

from gui import main_global as glb  # noqa: E402
from gui.config_panel import mark_index_gaps  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


def _entry(name, dance="SA", analyzed=True):
    e = MusicEntry(path=Path(f"C:/lib/lateincd/{dance}/{name}.mp3"),
                   title=name, dance=dance, bpm=51)
    e.features = [0.1] * 84 if analyzed else None
    return e


class _Lib:
    def __init__(self, entries):
        self.entries = list(entries)


class _Cache:
    """Covers exactly the files named in `measured`."""

    def __init__(self, measured=(), vocals=0):
        self._measured = set(measured)
        self._vocals = vocals

    def coverage_counts(self, paths, audio_fps=None):
        n = sum(1 for p in paths if Path(p).name in self._measured)
        return {"audiofp": n, "loudness": n, "silences": n, "pd": n}

    def audio_fp_keys(self):
        return set()

    def known_fingerprint(self, path):
        return f"FP:{Path(path).name}"

    def vocal_share_count(self):
        return self._vocals


class _Cfg:
    """ConfigPanel reduced to the one call that receives the block."""

    def __init__(self):
        self.msg = None

    def set_library_status(self, msg, **kw):
        self.msg = msg


class _Win:
    """MainWindow reduced to what the status block reads."""

    _mode_line = glb.GlobalIndexMixin._mode_line
    _refresh_library_status = glb.GlobalIndexMixin._refresh_library_status
    _index_summary = glb.GlobalIndexMixin._index_summary
    _global_index_line = glb.GlobalIndexMixin._global_index_line

    def __init__(self, lib, cache=None, global_lib=None, global_search=False):
        self._lib = lib
        self._cache = cache if cache is not None else _Cache()
        self._global_lib = global_lib
        self._settings = {"global_search": global_search}
        self._cfg = _Cfg()

    def _embedding_store(self):
        return None


class LibraryStatusI18nTest(unittest.TestCase):

    def setUp(self):
        # No global library loaded → the summary would ask the real DB how big
        # the repository index is. Keep the test off the disk.
        real = glb.planner.db.global_index_count
        glb.planner.db.global_index_count = lambda: 0
        self.addCleanup(setattr, glb.planner.db, "global_index_count", real)

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def status(self, language, **kw):
        """The block as the panel receives it, built by the real code."""
        i18n.set_active(language)
        win = _Win(kw.pop("lib", None) or _Lib([_entry("A"), _entry("B",
                                                                   analyzed=False)]),
                   cache=kw.pop("cache", None) or _Cache(measured={"A.mp3"}),
                   **kw)
        win._refresh_library_status()
        return win._cfg.msg

    # ── English must not move ────────────────────────────────────────────
    def test_english_is_unchanged(self):
        self.assertEqual(self.status("en"), "\n".join((
            "🎯  Search mode: Favorites library only",
            "Library: 2 files",
            "Favorites: 2",
            "🌐 Global index: not built (⚙ Settings to build)",
            "— Indexes (analyzed / total) —",
            "🔗 Fingerprints: Favorites 1/2",
            "🎚️ librosa: Favorites 1/2",
            "🎼 Chroma: (chroma not available)",
            "📊 Loudness: Favorites 1/2",
            "🔇 Silences: Favorites 1/2",
            "🐂 PD highlights: no Paso Doble in the library",
            "🧠 OpenL3: (OpenL3 not available)",
        )))

    # ── German ───────────────────────────────────────────────────────────
    def test_both_search_modes_speak_german(self):
        self.assertIn("🎯  Suchmodus: nur Favoriten-Bibliothek",
                      self.status("de"))
        self.assertIn("🌐  Suchmodus: Global — gesamtes Repository",
                      self.status("de", global_search=True))

    def test_the_counts_speak_german(self):
        msg = self.status("de")
        self.assertIn("Bibliothek: 2 Dateien", msg)
        self.assertIn("Favoriten: 2", msg)

    def test_the_index_headings_speak_german(self):
        msg = self.status("de")
        for line in ("— Indizes (analysiert / gesamt) —",
                     "🔗 Fingerabdrücke: ",
                     "📊 Lautheit: ",
                     "🔇 Stillen: ",
                     "🐂 PD-Höhepunkte: "):
            self.assertIn(line, msg)

    def test_the_scope_of_each_index_line_speaks_german(self):
        """'Favorites 1/2' is a label plus a count, and the label is chrome."""
        self.assertIn("🔗 Fingerabdrücke: Favoriten 1/2", self.status("de"))

    def test_a_model_that_is_not_installed_says_so_in_german(self):
        msg = self.status("de")
        self.assertIn("(Chroma nicht verfügbar)", msg)
        self.assertIn("(OpenL3 nicht verfügbar)", msg)
        self.assertIn("kein Paso Doble in der Bibliothek", msg)

    def test_the_demucs_line_speaks_german(self):
        msg = self.status("de", cache=_Cache(measured={"A.mp3"}, vocals=7))
        self.assertIn("🎙️ Demucs-Gesang: 7 gemessen", msg)

    def test_the_global_index_line_speaks_german_when_it_is_loaded(self):
        msg = self.status("de", global_lib=_Lib([_entry("R1"),
                                                 _entry("R2", analyzed=False)]))
        self.assertIn("🌐 Globaler Index: 2 Dateien, 1 analysiert", msg)

    def test_the_global_index_line_speaks_german_when_it_is_only_built(self):
        """The thousands separator stays the English one on purpose: nothing
        else in the app localises numbers, and doing it here alone would make
        this one line disagree with every other count on screen."""
        glb.planner.db.global_index_count = lambda: 1234
        self.assertIn(
            "🌐 Globaler Index: 1,234 Dateien gebaut (lädt bei der ersten "
            "globalen Suche)", self.status("de"))

    def test_the_global_index_line_speaks_german_when_it_is_missing(self):
        self.assertIn("🌐 Globaler Index: nicht gebaut (⚙ Einstellungen zum "
                      "Bauen)", self.status("de"))

    # ── the amber gap marking must survive the translation ───────────────
    def test_a_short_count_is_still_painted_amber_in_german(self):
        painted = mark_index_gaps(self.status("de"))
        self.assertIn('<span style="color:#c77700">1</span>/2', painted)

    def test_the_numbers_themselves_are_never_translated(self):
        """A count that happened to match a catalog key must stay a count."""
        msg = self.status("de", lib=_Lib([_entry("A")]))
        self.assertIn("Bibliothek: 1 Dateien", msg)


class BuildAllTooltipI18nTest(unittest.TestCase):
    """The 🧱 button under the block — its tooltip is assembled the same way."""

    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def tip(self, language, n_unanalyzed):
        i18n.set_active(language)
        from gui.config_panel import ConfigPanel
        panel = ConfigPanel()
        self.addCleanup(panel.deleteLater)
        panel.set_library_status("x", n_unanalyzed=n_unanalyzed,
                                 needs_build=True)
        return panel.build_all_btn.toolTip()

    def test_english_is_unchanged(self):
        self.assertEqual(self.tip("en", 3),
                         "🧱 Build ALL caches — 3 file(s) in the favorites "
                         "library have no\nanalysis yet. Asks for the scope\n"
                         "first; reuses everything already cached and can be "
                         "cancelled.")

    def test_the_unanalyzed_count_speaks_german(self):
        tip = self.tip("de", 3)
        self.assertIn("🧱 ALLE Caches aufbauen", tip)
        self.assertIn("3 Datei(en)", tip)

    def test_the_incomplete_index_wording_speaks_german(self):
        self.assertIn("ein Index der Favoriten-Bibliothek ist noch nicht "
                      "vollständig", self.tip("de", 0))


if __name__ == "__main__":
    unittest.main()
