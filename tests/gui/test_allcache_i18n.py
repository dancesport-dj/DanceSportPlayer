#!/usr/bin/env python3
"""🧱 Build ALL caches — the scope question, the report and the notes, in German.

Run:  py -m unittest tests.gui.test_allcache_i18n -v

Same shape as the library-status block: nothing here reaches a widget as a
whole literal. The confirmation names the step list it just planned, the
closing box names the steps it ran and the scope it ran them over, and every
failure note carries a count — so each of them is assembled and matches no
catalog key.

Two things this pins beyond the words:

* `_ALLCACHE_NAMES` stays English. Its values are identity as well as label —
  they key `st["reports"]` and travel through `_allcache_step_done` — so the
  translation happens where they are rendered, never in the dict.
* The scope label ("the favorites library") is read in two grammatical
  positions. German needs a different case after "aus" than after "für", so
  the question was reshaped to name the scope on its own line instead of
  bending one German form to fit both.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_allcache_i18n_"))

from gui import main_allcache as mac  # noqa: E402
from planner import i18n  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


def _entry(name, dance="SA"):
    return MusicEntry(path=Path(f"C:/lib/lateincd/{dance}/{name}.mp3"),
                      title=name, dance=dance, bpm=51)


class _Box:
    """Records what a QMessageBox was asked to show, and answers Yes."""

    class StandardButton:
        Yes = 1
        No = 0

    def __init__(self):
        self.shown = []

    def question(self, parent, title, text, buttons=None):
        self.shown.append(("question", title, text))
        return self.StandardButton.Yes

    def information(self, parent, title, text):
        self.shown.append(("information", title, text))

    def warning(self, parent, title, text):
        self.shown.append(("warning", title, text))

    def critical(self, parent, title, text):
        self.shown.append(("critical", title, text))

    def last(self):
        return self.shown[-1][2]


class _Bar:
    def __init__(self):
        self.msg = None

    def showMessage(self, msg):
        self.msg = msg


class _Win:
    """MainWindow reduced to what the build-all messages are assembled from."""

    _do_build_all_caches = mac.AllCacheMixin._do_build_all_caches
    _allcache_next = mac.AllCacheMixin._allcache_next
    _allcache_step_done = mac.AllCacheMixin._allcache_step_done
    _allcache_reason = staticmethod(mac.AllCacheMixin._allcache_reason)
    _allcache_cancel = mac.AllCacheMixin._allcache_cancel

    def __init__(self, pool=None, label="the favorites library",
                 steps=("audiofp", "librosa"), skipped=(), why=""):
        self._pool = list(pool or [_entry("A"), _entry("B"), _entry("C")])
        self._label = label
        self._plan = (why, list(steps), list(skipped))
        self._busy = None
        self._emb_store_cache = None
        self._allcache = None
        self._bar = _Bar()

    # what the flow calls into, and this test is not about
    def _scoped_pool(self, scope, name):
        return self._pool, self._label

    def _plan_allcache(self, pool):
        return self._plan

    def _run_behind_busy(self, message, fn):
        return fn(lambda _c: None)

    def _refresh_library_status(self, *a, **kw):
        pass

    def _sync_loudness_available(self):
        pass

    def _allcache_advance(self):
        pass

    # the workers themselves: the real _allcache_next still dispatches to them,
    # so the pipeline's own step choice stays under test — only the QThread is
    # not started.
    def _allcache_run_librosa(self, pool):
        self.ran = ("librosa", pool)

    def _allcache_run_probe(self, step, name, pool):
        self.ran = (step, name, pool)

    def _allcache_run_embedding(self, model, name, pool):
        self.ran = (model, name, pool)

    def statusBar(self):
        return self._bar


class _I18nCase(unittest.TestCase):

    def setUp(self):
        self.box = _Box()
        real_box = mac.QMessageBox
        mac.QMessageBox = self.box
        self.addCleanup(setattr, mac, "QMessageBox", real_box)
        real_cleanup = mac.planner.db.cleanup_orphans
        mac.planner.db.cleanup_orphans = lambda *a, **kw: None
        self.addCleanup(setattr, mac.planner.db, "cleanup_orphans", real_cleanup)

    def tearDown(self):
        i18n.set_active(i18n.DEFAULT_LANGUAGE)


class PlanSkipNotesI18nTest(_I18nCase):
    """The 'what this machine cannot build' notes, straight off the planner."""

    def plan(self, language, **kw):
        i18n.set_active(language)
        args = dict(has_pd=True, have_librosa=True, have_ffmpeg=True,
                    have_openl3=True, have_chroma=True)
        args.update(kw)
        return mac.plan_allcache_steps(**args)[1]

    def test_english_is_unchanged(self):
        self.assertEqual(self.plan("en", have_ffmpeg=False, have_librosa=False,
                                   have_openl3=False, have_chroma=False),
                         ["librosa audio analysis (no working audio decoder)",
                          "loudness + silences (no ffmpeg)",
                          "OpenL3 (not installed)",
                          "Chroma (not installed)"])

    def test_german_names_every_missing_piece(self):
        self.assertEqual(self.plan("de", have_ffmpeg=False, have_librosa=False,
                                   have_openl3=False, have_chroma=False),
                         ["librosa-Audioanalyse (kein funktionierender Decoder)",
                          "Lautheit + Stillen (kein ffmpeg)",
                          "OpenL3 (nicht installiert)",
                          "Chroma (nicht installiert)"])

    def test_the_step_keys_are_never_translated(self):
        """They pick the worker and key the per-step reports."""
        i18n.set_active("de")
        steps, _ = mac.plan_allcache_steps(
            has_pd=True, have_librosa=True, have_ffmpeg=True,
            have_openl3=True, have_chroma=True)
        self.assertEqual(steps, ["audiofp", "librosa", "loudness", "silences",
                                 "pd", "openl3", "chroma"])


class ScopeQuestionI18nTest(_I18nCase):

    def ask(self, language, **kw):
        i18n.set_active(language)
        win = _Win(**kw)
        win._do_build_all_caches("local")
        return self.box.last()

    def test_english_is_unchanged(self):
        self.assertEqual(self.ask("en"), (
            "Build every index over 3 tracks from the favorites library?\n\n"
            "Runs audio fingerprints → librosa back-to-back. Each is slow the "
            "first time, then cached; reuses anything already built. You can "
            "cancel between or within steps.\n\n"
            "Read-only — your audio files are never modified."))

    def test_german_names_the_scope_on_its_own_line(self):
        text = self.ask("de")
        self.assertIn("Jeden Index über 3 Titel aufbauen?", text)
        self.assertIn("Umfang: die Favoriten-Bibliothek", text)

    def test_german_names_the_steps_it_will_run(self):
        self.assertIn("Läuft: Audio-Fingerabdrücke → librosa", self.ask("de"))

    def test_german_says_it_will_not_touch_the_audio(self):
        self.assertIn("Nur lesend — deine Audiodateien werden nie verändert.",
                      self.ask("de"))

    def test_the_skip_note_speaks_german(self):
        self.assertIn("Übersprungen: Lautheit + Stillen (kein ffmpeg)",
                      self.ask("de", skipped=["Lautheit + Stillen (kein ffmpeg)"]))

    def test_a_machine_that_can_build_nothing_says_so_in_german(self):
        self.assertIn("Auf diesem Rechner kann gerade nichts gebaut werden.",
                      self.ask("de", steps=()))

    def test_the_whole_repository_scope_speaks_german(self):
        self.assertIn("Umfang: das gesamte Repository",
                      self.ask("de", label="the whole repository"))

    def test_the_combined_scope_speaks_german(self):
        self.assertIn("Umfang: das gesamte Repository + die Favoriten-Bibliothek",
                      self.ask("de", label="the whole repository + favorites library"))


class ClosingReportI18nTest(_I18nCase):

    def finish(self, language, notes=(), skips=()):
        i18n.set_active(language)
        win = _Win()
        win._allcache = {"pool": [], "label": "the favorites library",
                         "steps": ["audiofp", "librosa"],
                         "names": mac._ALLCACHE_NAMES, "models": {}, "i": 2,
                         "notes": list(notes), "skips": list(skips),
                         "reports": {}}
        win._allcache_next()
        return win._bar.msg, self.box.last()

    def test_english_is_unchanged(self):
        bar, text = self.finish("en")
        self.assertEqual(bar, "All caches built for the favorites library.")
        self.assertEqual(text, "All caches are built for the favorites library.\n"
                               "Ran: audio fingerprints, librosa.")

    def test_a_clean_run_speaks_german(self):
        bar, text = self.finish("de")
        self.assertEqual(bar, "Alle Caches gebaut für die Favoriten-Bibliothek.")
        self.assertIn("Alle Caches sind gebaut für die Favoriten-Bibliothek.", text)
        self.assertIn("Gelaufen: Audio-Fingerabdrücke, librosa.", text)

    def test_a_run_with_problems_speaks_german(self):
        bar, text = self.finish("de", notes=["librosa: 2 file(s) failed"])
        self.assertIn("mit Problemen, siehe Log", bar)
        self.assertIn("Fertig für die Favoriten-Bibliothek, aber nicht alles "
                      "hat geklappt:", text)

    def test_the_unbuildable_files_are_named_in_german(self):
        _, text = self.finish("de", skips=["librosa: 1 file(s) skipped"])
        self.assertIn("Dafür konnte nichts gebaut werden, und daran ändert sich "
                      "nichts:", text)


class StepNoteI18nTest(_I18nCase):

    def note(self, language, rep, name="librosa", ok=7, errors=2):
        i18n.set_active(language)
        win = _Win()
        win._allcache = {"notes": [], "reports": {name: rep}}
        win._allcache_step_done(name, ok, errors)
        return win._allcache

    def test_english_is_unchanged(self):
        st = self.note("en", {"reasons": {"no decoder": 2}})
        self.assertEqual(st["notes"],
                         ["librosa: 2 file(s) failed (no decoder), 7 cached"])

    def test_a_failure_note_speaks_german(self):
        st = self.note("de", {"reasons": {"no decoder": 2}})
        self.assertEqual(st["notes"],
                         ["librosa: 2 Datei(en) fehlgeschlagen (no decoder), "
                          "7 zwischengespeichert"])

    def test_the_commonest_reason_is_labelled_in_german(self):
        st = self.note("de", {"reasons": {"no decoder": 2, "bad tag": 1}})
        self.assertIn("meist: no decoder", st["notes"][0])

    def test_a_file_gone_from_disk_is_reported_apart_in_german(self):
        st = self.note("de", {"skipped": 3}, errors=0)
        self.assertEqual(st["skips"],
                         ["librosa: 3 Datei(en) übersprungen — nicht mehr "
                          "auf der Platte"])

    def test_the_step_name_is_translated_where_it_is_shown(self):
        st = self.note("de", {"reasons": {"x": 1}}, name="audio fingerprints",
                       errors=1)
        self.assertTrue(st["notes"][0].startswith("Audio-Fingerabdrücke: "))


class CancelMessageI18nTest(_I18nCase):

    def test_english_is_unchanged(self):
        i18n.set_active("en")
        win = _Win()
        win._allcache_cancel("librosa", 12)
        self.assertEqual(win._bar.msg, "Build all caches cancelled during "
                                       "librosa — 12 done so far (cached).")

    def test_german(self):
        i18n.set_active("de")
        win = _Win()
        win._allcache_cancel("librosa", 12)
        self.assertEqual(win._bar.msg, "Alle Caches aufbauen — abgebrochen bei "
                                       "librosa, 12 bisher fertig "
                                       "(zwischengespeichert).")


if __name__ == "__main__":
    unittest.main()
