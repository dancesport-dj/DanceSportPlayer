#!/usr/bin/env python3
"""Tests for what the startup does BEFORE the window appears — and what it no
longer does there.

Run:  py -m unittest tests.app.test_startup_deferred -v

Filling the library browser, learning vocal/instrumental and counting which
tracks are indexed used to happen in front of the splash screen, and together
they were most of the wait: the window opened only once every last one of them
had finished. They now run behind the open window, one per turn of the event
loop, reporting themselves in the status bar. Two things therefore have to
hold: the window must come up before any of them, and every one of them must
still actually run.
"""

import os
import tempfile
import unittest

# Offscreen BEFORE any QApplication exists, and state files into a temp dir (the
# gui modules resolve those at import time — see test_gui_smoke.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_startup_"))

from PySide6.QtWidgets import QApplication    # noqa: E402

from gui import main_global as gmg                 # noqa: E402
from planner import i18n                           # noqa: E402


class _Bar:
    def __init__(self, log):
        self._log = log

    def showMessage(self, msg):
        self._log.append(f"status: {msg}")


class _Splash:
    def __init__(self, log):
        self._log = log

    def set_status(self, msg):
        self._log.append(f"splash: {msg}")

    def accept(self):
        self._log.append("splash closed")


class _Entries:
    """The library browser and the 🏆 tree, which only get told the list."""

    def __init__(self, log, name):
        self._log = log
        self._name = name

    def set_entries(self, entries):
        self._log.append(f"{self._name}: {len(entries)} entries")


class _Lib:
    def __init__(self, n=3):
        self.entries = [_Track() for _ in range(n)]


class _Track:
    dance = "LW"
    features = None
    path = "song.mp3"


class _Win:
    """A MainWindow reduced to the load path, recording what happens in order."""

    _on_library_loaded = gmg.GlobalIndexMixin._on_library_loaded
    _finish_library_load = gmg.GlobalIndexMixin._finish_library_load

    def __init__(self):
        self.log = []
        self._all_tables = []
        self._loading_dlg = _Splash(self.log)
        self._lib_browser = _Entries(self.log, "browser")
        self._tourney_tree = _Entries(self.log, "tree")
        self._bar = _Bar(self.log)
        self._lib = None
        self._cache = None

    def statusBar(self):
        return self._bar

    def show(self):
        self.log.append("WINDOW SHOWN")

    def _restore_playlist(self):
        self.log.append("restore")

    def _seed_undo_baseline(self):
        self.log.append("undo baseline")

    def _refresh_library_status(self, enable_generate=False):
        self.log.append(f"library status (generate={enable_generate})")

    def _sync_loudness_available(self):
        self.log.append("loudness available")


class _StartupCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        # The real one pushes the app icon onto a taskbar button that no
        # headless window has, and the vocal learning wants real features.
        for name in ("apply_taskbar_icon", "learn_instrumental_probs",
                     "apply_vocal_shares"):
            self.addCleanup(setattr, gmg, name, getattr(gmg, name))
        gmg.apply_taskbar_icon = lambda _win: None
        gmg.learn_instrumental_probs = lambda entries: self.win.log.append(
            "learned vocals")
        gmg.apply_vocal_shares = lambda entries, cache: None
        self.win = _Win()

    def _load(self):
        self.win._on_library_loaded(_Lib(), object())
        self._settle()
        return self.win.log

    def _settle(self):
        """Run the deferred steps out — they hand back to the event loop
        between each one, so a single processEvents is not enough."""
        for _ in range(20):
            self.app.processEvents()


class DeferredStartupTest(_StartupCase):

    def test_the_window_opens_before_the_slow_part(self):
        log = self._load()
        shown = log.index("WINDOW SHOWN")
        for later in ("learned vocals", "browser: 3 entries",
                      "library status (generate=True)"):
            self.assertGreater(log.index(later), shown, later)

    def test_only_the_last_session_is_restored_in_front_of_the_splash(self):
        log = self._load()
        shown = log.index("WINDOW SHOWN")
        self.assertLess(log.index("restore"), shown)
        self.assertLess(log.index("undo baseline"), shown)
        self.assertEqual(log.index("splash closed"), shown - 1)

    def test_everything_deferred_still_runs(self):
        log = self._load()
        for step in ("learned vocals", "browser: 3 entries", "tree: 3 entries",
                     "library status (generate=True)", "loudness available"):
            self.assertIn(step, log)

    def test_each_step_says_what_it_is_doing_before_it_does_it(self):
        """A message posted and then overwritten inside one call is a message
        nobody ever sees — that is why they run one per event-loop turn."""
        log = self._load()
        for msg, step in (("🎙️", "learned vocals"),
                          ("📚", "browser: 3 entries"),
                          ("🔬", "library status (generate=True)")):
            said = next(i for i, line in enumerate(log)
                        if line.startswith("status: ") and msg in line)
            self.assertLess(said, log.index(step), msg)

    def test_it_ends_on_the_library_summary(self):
        log = self._load()
        self.assertEqual(log[-1], "status: Library loaded — 3 MP3 files, "
                                  "3 favorites songs, 0 audio cached.")

    def test_the_library_is_reachable_the_moment_the_window_is_up(self):
        """Deferring the tail must not defer the library itself: everything the
        open window offers to do reads self._lib."""
        self.win._on_library_loaded(_Lib(), "the cache")
        self.assertEqual(len(self.win._lib.entries), 3)
        self.assertEqual(self.win._cache, "the cache")
        self._settle()


class LibrarySummaryLanguageTest(_StartupCase):
    """The line the status bar is left on after the load.

    It was built as an f-string, so there was no key for the catalog to
    match and the hook on `QStatusBar.showMessage` never had a chance — a
    German screen ended its startup in English. `i18n.t("… %s …") % …`
    makes the sentence a key again and interpolates afterwards.
    """

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)

    def summary(self, language):
        i18n.set_active(language)
        return self._load()[-1]

    def test_english_is_unchanged(self):
        self.assertEqual(self.summary("en"),
                         "status: Library loaded — 3 MP3 files, "
                         "3 favorites songs, 0 audio cached.")

    def test_the_load_ends_in_german(self):
        self.assertEqual(self.summary("de"),
                         "status: Bibliothek geladen — 3 MP3-Dateien, "
                         "3 Favoriten-Titel, 0 im Audio-Cache.")


if __name__ == "__main__":
    unittest.main()
