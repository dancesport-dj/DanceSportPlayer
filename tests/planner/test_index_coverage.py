"""Tests for the "analyzed / total" counters and the too-short embedding skip.

Three things the Settings dialog and the left-hand library panel now claim:
  • AudioCache.coverage_counts says how many tracks have loudness / silences /
    PD highlights — from the in-memory mirror only, so it must never touch disk
  • an FX sample that is shorter than a descriptor is a SKIP, not an error, and
    must not colour the failure count of a whole index run
  • 🧱 Build ALL caches runs every one of them, playback caches first — behind a
    please-wait bar while it works out which of them this machine can run
"""
import logging
import os
import sqlite3
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path

from planner import embeddings as ae
from planner.embeddings import AudioTooShort
from planner.db import AudioCache


class _Cache:
    """Just the four caches and the fingerprint mirror coverage_counts reads."""

    coverage_counts = AudioCache.coverage_counts

    def __init__(self):
        self._fp = {"a.mp3": "FA", "b.mp3": "FB", "c.mp3": "FC"}
        self._lufs = {"FA": -14.0, "FB": -12.0}
        self._silences = {"FA": []}
        self._pd_hl = {"FC": 42.0}
        self.queries = 0

    def known_fingerprint(self, path):
        return self._fp.get(Path(path).name)

    def audio_fp_keys(self):
        self.queries += 1
        return {"FA", "FC"}


class CoverageCountsTest(unittest.TestCase):

    def test_counts_each_cache_separately(self):
        got = _Cache().coverage_counts([Path("x/a.mp3"), Path("x/b.mp3"),
                                        Path("x/c.mp3")])
        self.assertEqual(got, {"audiofp": 2, "loudness": 2,
                               "silences": 1, "pd": 1})

    def test_unfingerprinted_files_count_as_unanalyzed(self):
        got = _Cache().coverage_counts([Path("x/a.mp3"), Path("x/never_seen.mp3")])
        self.assertEqual(got, {"audiofp": 1, "loudness": 1,
                               "silences": 1, "pd": 0})

    def test_no_paths_is_all_zero(self):
        self.assertEqual(_Cache().coverage_counts([]),
                         {"audiofp": 0, "loudness": 0, "silences": 0, "pd": 0})

    def test_a_handed_in_fingerprint_set_spares_the_query(self):
        """🔗 has no in-memory mirror, so a summary over two libraries hands the
        same set to both calls instead of querying twice."""
        cache = _Cache()
        got = cache.coverage_counts([Path("x/a.mp3"), Path("x/b.mp3")],
                                    {"FB"})
        self.assertEqual(got["audiofp"], 1)
        self.assertEqual(cache.queries, 0)


class EmbeddingFpsTest(unittest.TestCase):
    """Counting coverage must not drag every vector out of the database.

    "🧠 OpenL3: Favorites 2,900/3,510" used to be answered by asking the store
    for each entry's embedding, which loaded and unpacked all 53k vectors of
    every model — five seconds of every single startup, for three numbers on a
    label nobody had asked to be exact about.
    """

    def setUp(self):
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        self.addCleanup(setattr, ae, "_db", ae._db)
        ae._db = lambda: conn
        self.store = ae.EmbeddingStore(cache=None)
        for fp, model in (("FA", "openl3"), ("FB", "openl3"), ("FA", "chroma2dftm")):
            conn.execute("INSERT INTO embeddings (fp, model, vec) VALUES (?,?,?)",
                         (fp, model, ae.EmbeddingStore._pack([1.0, 2.0])))

    def test_only_the_model_asked_for_is_counted(self):
        self.assertEqual(self.store.fps("openl3"), {"FA", "FB"})
        self.assertEqual(self.store.fps("chroma2dftm"), {"FA"})

    def test_a_model_with_nothing_indexed_is_empty(self):
        self.assertEqual(self.store.fps("nothing_here"), set())

    def test_the_vectors_are_never_unpacked(self):
        """The whole point: keys are read, blobs are left in the database."""
        self.addCleanup(setattr, ae.EmbeddingStore, "_unpack",
                        ae.EmbeddingStore._unpack)
        ae.EmbeddingStore._unpack = staticmethod(
            lambda blob: self.fail("a vector was unpacked to count it"))
        self.assertEqual(self.store.fps("openl3"), {"FA", "FB"})

    def test_the_keys_are_read_once(self):
        self.store.fps("openl3")
        ae._db = lambda: self.fail("the key set was read a second time")
        self.assertEqual(self.store.fps("openl3"), {"FA", "FB"})

    def test_a_new_embedding_is_in_the_set(self):
        """A put loads the mirror, and the mirror is what fps then answers from
        — so there is no stale key set to invalidate."""
        self.store.fps("openl3")            # keys-only view first
        self.store.put("FC", "openl3", [3.0, 4.0])
        self.assertEqual(self.store.fps("openl3"), {"FA", "FB", "FC"})

    def test_a_loaded_mirror_answers_instead_of_the_database(self):
        self.store._load_model("openl3")
        ae._db = lambda: self.fail("the mirror was already in memory")
        self.assertEqual(self.store.fps("openl3"), {"FA", "FB"})


class BuildAllStepsTest(unittest.TestCase):
    """🧱 Build ALL caches has to mean all of them, in a useful order."""

    @staticmethod
    def _plan(**kw):
        # Lazy import, same reason as test_pd_analyze: gui.main_allcache pulls in
        # modules that resolve the GUI state files at import time.
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from gui.main_allcache import plan_allcache_steps
        args = dict(has_pd=True, have_librosa=True, have_ffmpeg=True,
                    have_openl3=True, have_chroma=True)
        args.update(kw)
        return plan_allcache_steps(**args)

    def test_everything_installed_runs_playback_caches_first(self):
        steps, skipped = self._plan()
        self.assertEqual(steps, ["audiofp", "librosa", "loudness", "silences", "pd",
                                 "openl3", "chroma"])
        self.assertEqual(skipped, [])

    def test_no_ffmpeg_drops_only_the_ffmpeg_steps(self):
        steps, skipped = self._plan(have_ffmpeg=False)
        self.assertEqual(steps, ["audiofp", "librosa", "pd", "openl3", "chroma"])
        self.assertEqual(skipped, ["loudness + silences (no ffmpeg)"])

    def test_library_without_paso_doble_skips_highlights_silently(self):
        steps, skipped = self._plan(has_pd=False)
        self.assertNotIn("pd", steps)
        self.assertEqual(skipped, [])

    def test_no_audio_decoder_drops_librosa_and_says_so(self):
        # Running it anyway means failing on every file and then reporting
        # success — the bug this skip exists for.
        steps, skipped = self._plan(have_librosa=False)
        self.assertNotIn("librosa", steps)
        self.assertEqual(steps, ["audiofp", "loudness", "silences", "pd",
                                 "openl3", "chroma"])
        self.assertIn("librosa audio analysis (no working audio decoder)", skipped)

    def test_a_machine_with_nothing_installed_plans_nothing(self):
        steps, _ = self._plan(has_pd=False, have_librosa=False, have_ffmpeg=False,
                              have_openl3=False, have_chroma=False)
        self.assertEqual(steps, [])

    def test_missing_models_are_named_in_the_skip_note(self):
        steps, skipped = self._plan(have_openl3=False, have_chroma=False)
        self.assertEqual(steps, ["audiofp", "librosa", "loudness", "silences", "pd"])
        self.assertEqual(skipped, ["OpenL3 (not installed)",
                                   "Chroma (not installed)"])

    def test_the_audio_fingerprints_go_first_or_not_at_all(self):
        """They keep everything the other steps build attached across a tag edit,
        so they belong in front of them — and nowhere on their own."""
        self.assertEqual(self._plan(have_librosa=False, have_ffmpeg=False,
                                    has_pd=False, have_chroma=False)[0],
                         ["audiofp", "openl3"])
        self.assertNotIn("audiofp", self._plan(has_pd=False, have_librosa=False,
                                               have_ffmpeg=False, have_openl3=False,
                                               have_chroma=False)[0])


class _FakeBusy:
    """BusyDialog reduced to the order the calls have to come in."""

    log = []

    def __init__(self, parent, message=""):
        self.log.append(("open", message))

    def show_after(self, ms):
        self.log.append(("show_after", ms))

    def set_message(self, msg):
        self.log.append(("message", msg))

    def finish(self):
        self.log.append(("finish", None))


class PlanBusyTest(unittest.TestCase):
    """The seconds before the confirmation must not look like a hang."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _plan(self, probe=lambda pool: ""):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from gui import main_allcache as gmg

        class _Win(gmg.AllCacheMixin):
            _librosa_unavailable = staticmethod(probe)

        _FakeBusy.log = []
        with mock.patch.object(gmg, "BusyDialog", _FakeBusy), \
             mock.patch.object(gmg, "find_ffmpeg", lambda: None), \
             mock.patch.object(ae, "openl3_available", lambda: False), \
             mock.patch.object(ae, "chroma_available", lambda: False):
            return _Win()._plan_allcache([]), _FakeBusy.log

    def test_the_wait_is_shown_at_once_and_closed_again(self):
        """The checks run in a worker, so the event loop is free to draw the bar;
        a bar left open under the next message box cannot be dismissed."""
        _, log = self._plan()
        self.assertEqual(log[0][0], "open")
        self.assertEqual(log[1], ("show_after", 0))
        self.assertEqual(log[-1], ("finish", None))
        self.assertIn("message", [c[0] for c in log])

    def test_the_checks_do_not_run_on_the_ui_thread(self):
        """The whole reason for the worker: painting needs the event loop back."""
        import threading
        seen = []

        def _probe(pool):
            seen.append(threading.current_thread() is threading.main_thread())
            return ""

        self._plan(probe=_probe)
        self.assertEqual(seen, [False])

    def test_the_plan_is_the_same_one_as_before(self):
        (why, steps, skipped), _ = self._plan()
        self.assertEqual(why, "")
        self.assertEqual(steps, ["audiofp", "librosa"])   # no ffmpeg, no models
        self.assertIn("loudness + silences (no ffmpeg)", skipped)

    def test_a_failing_check_still_closes_the_wait(self):
        def _boom(pool):
            raise RuntimeError("probe exploded")

        with self.assertRaises(RuntimeError):
            self._plan(probe=_boom)
        self.assertEqual(_FakeBusy.log[-1], ("finish", None))


class CleanupBusyTest(unittest.TestCase):
    """Saying Yes must not buy a second frozen window.

    The confirmed rebuild reclaims dead DB rows first, and that stats every
    registered path — 58,510 of them here, 4.5s with the drives plugged in and
    the cache warm. On the UI thread that is the same hang the please-wait bar
    was added to cure, just moved behind the question.
    """

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def _build(self, cleanup):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from PySide6.QtWidgets import QMessageBox
        from gui import main_allcache as gmg

        class _Win(gmg.AllCacheMixin):
            _scoped_pool = staticmethod(lambda scope, title: ([], "the favorites"))
            _plan_allcache = staticmethod(lambda pool: ("", ["librosa"], []))
            _allcache_next = staticmethod(lambda: None)

        class _Yes:
            StandardButton = QMessageBox.StandardButton
            question = staticmethod(
                lambda *a, **k: QMessageBox.StandardButton.Yes)
            information = warning = staticmethod(lambda *a, **k: None)

        _FakeBusy.log = []
        win = _Win()
        with mock.patch.object(gmg, "BusyDialog", _FakeBusy), \
             mock.patch.object(gmg, "QMessageBox", _Yes), \
             mock.patch.object(gmg.planner.db, "cleanup_orphans", cleanup):
            win._do_build_all_caches("all")
        return win, _FakeBusy.log

    def test_the_orphan_scan_does_not_run_on_the_ui_thread(self):
        """Stat'ing a whole library is exactly the kind of work the bar covers."""
        import threading
        seen = []

        def _cleanup():
            seen.append(threading.current_thread() is threading.main_thread())
            return {}

        self._build(_cleanup)
        self.assertEqual(seen, [False])

    def test_the_wait_is_shown_at_once_and_closed_again(self):
        _, log = self._build(lambda: {})
        self.assertEqual(log[0][0], "open")
        self.assertEqual(log[1], ("show_after", 0))
        self.assertEqual(log[-1], ("finish", None))

    def test_a_failing_cleanup_still_builds_the_caches(self):
        """Reclaiming rows is housekeeping — it must never cost the rebuild."""
        def _boom():
            raise RuntimeError("db locked")

        win, log = self._build(_boom)
        self.assertEqual(log[-1], ("finish", None))
        self.assertEqual(win._allcache["steps"], ["librosa"])


class AudioFpPassTest(unittest.TestCase):
    """The pass that puts the audio fingerprints on record for an old library."""

    @staticmethod
    def _pass(paths, have, recorded=()):
        from gui.workers import AudioFpAnalyzer

        class _Cache:
            def __init__(self):
                self.asked = []

            def audio_fp_keys(self):
                return set(have)

            def known_fingerprint(self, path):
                return recorded[0].get(str(path)) if recorded else None

            def ensure_audio_fp(self, path):
                self.asked.append(str(path))
                return True

        cache = _Cache()
        return AudioFpAnalyzer(cache, [Path(p) for p in paths]), cache

    def test_a_file_already_on_record_is_not_read_again(self):
        known = {"a.mp3": "FA", "b.mp3": "FB"}
        worker, _ = self._pass(["a.mp3", "b.mp3"], have={"FA"}, recorded=(known,))
        self.assertEqual([p.name for p in worker.todo()], ["b.mp3"])

    def test_a_file_never_hashed_is_included(self):
        worker, _ = self._pass(["new.mp3"], have={"FA"}, recorded=({},))
        self.assertEqual([p.name for p in worker.todo()], ["new.mp3"])

    def test_measuring_records_the_fingerprint(self):
        worker, cache = self._pass(["a.mp3"], have=set())
        self.assertTrue(worker.measure(Path("a.mp3")))
        self.assertEqual(cache.asked, ["a.mp3"])


class _Boxes:
    """Stands in for QMessageBox and records which box was shown."""

    def __init__(self):
        self.calls = []

    def information(self, _parent, title, text):
        self.calls.append(("information", title, text))

    def warning(self, _parent, title, text):
        self.calls.append(("warning", title, text))

    def critical(self, _parent, title, text):
        self.calls.append(("critical", title, text))


class _Bar:
    def __init__(self):
        self.msg = ""

    def showMessage(self, msg):
        self.msg = msg


def _report_window(gmg, steps):
    """A bare AllCacheMixin carrying only what the build-all bookkeeping reads."""

    class _Win(gmg.AllCacheMixin):
        def __init__(self):
            self._bar = _Bar()
            self._busy = None
            self._emb_store_cache = None
            self._allcache = {"pool": [], "label": "the library", "steps": steps,
                              "names": gmg._ALLCACHE_NAMES, "models": {},
                              "i": len(steps) - 1, "notes": []}

        def statusBar(self):
            return self._bar

        def _refresh_library_status(self, *a, **kw):
            pass

        def _sync_loudness_available(self):
            self.synced += 1

        synced = 0

    return _Win()


class BuildAllReportTest(unittest.TestCase):
    """A step that failed on every file must not read as a success.

    The pipeline used to discard every worker's error count and close with
    "All caches are built" — so a machine that could not decode a single MP3
    got a green light and a permanently greyed-out "Find similar tracks".
    """

    def setUp(self):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from gui import main_allcache as gmg
        self.gmg = gmg
        self.boxes = _Boxes()
        self.addCleanup(setattr, gmg, "QMessageBox", gmg.QMessageBox)
        gmg.QMessageBox = self.boxes
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_a_clean_run_still_reports_success(self):
        win = _report_window(self.gmg, ["librosa"])
        win._allcache_step_done("librosa", 120, 0)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "information")
        self.assertIn("All caches are built", text)
        self.assertIn("All caches built", win._bar.msg)

    def test_failures_are_named_instead_of_claiming_success(self):
        win = _report_window(self.gmg, ["librosa"])
        win._allcache_step_done("librosa", 0, 3638)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "warning")
        self.assertNotIn("All caches are built", text)
        self.assertIn("librosa", text)
        self.assertIn("3,638", text)
        self.assertIn("problems", win._bar.msg)

    def test_an_earlier_step_s_failure_survives_to_the_final_report(self):
        win = _report_window(self.gmg, ["librosa", "loudness"])
        win._allcache["i"] = 0
        # librosa fails partway; loudness then runs over an empty pool and falls
        # straight through to the closing report, which must still say so.
        win._allcache_step_done("librosa", 5, 7)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "warning")
        self.assertIn("librosa: 7 file(s) failed", text)

    def test_the_pipeline_state_is_cleared_before_the_box_is_shown(self):
        # The box is modal: leaving _allcache set would let a second click of
        # "Build ALL caches" resume a finished pipeline.
        seen = []
        self.boxes.information = lambda *a: seen.append(getattr(win, "_allcache"))
        win = _report_window(self.gmg, ["librosa"])
        win._allcache_step_done("librosa", 1, 0)
        self.assertEqual(seen, [None])


class LibrosaUnavailableTest(unittest.TestCase):
    """The probe verdict has to reach the user as something actionable."""

    def setUp(self):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from gui import main_allcache as gmg
        self.gmg = gmg
        self.probed = []
        self.addCleanup(setattr, gmg.planner.db, "probe_decode_backend",
                        gmg.planner.db.probe_decode_backend)
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def _why(self, reason, pool=(Path("Tango 32.mp3"),)):
        def _probe(path):
            self.probed.append(path)
            return reason

        self.gmg.planner.db.probe_decode_backend = _probe
        win = _report_window(self.gmg, ["librosa"])
        entries = [types.SimpleNamespace(path=p) for p in pool]
        return win._librosa_unavailable(entries)

    def test_a_working_decoder_raises_no_objection(self):
        self.assertEqual(self._why(None), "")

    def test_missing_librosa_names_the_pip_command(self):
        self.assertIn("pip install librosa", self._why(self.gmg.planner.db.PROBE_NO_LIBROSA))

    def test_a_missing_decoder_points_at_ffmpeg_on_path(self):
        # find_ffmpeg() also accepts a copy bundled next to the app, which
        # audioread cannot use — so the wording has to insist on PATH.
        msg = self._why(self.gmg.planner.db.PROBE_NO_BACKEND)
        self.assertIn("ffmpeg", msg)
        self.assertIn("PATH", msg)

    def test_any_other_failure_names_the_file_and_the_log(self):
        msg = self._why(self.gmg.planner.db.PROBE_FAILED)
        self.assertIn("Tango 32.mp3", msg)
        self.assertIn("log", msg)

    def test_an_empty_pool_is_not_probed_at_all(self):
        self.assertEqual(self._why(self.gmg.planner.db.PROBE_NO_BACKEND, pool=()), "")
        self.assertEqual(self.probed, [])


class DecodeProbeTest(unittest.TestCase):
    """One probe up front, so a library-wide decode failure has a name."""

    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def _probe(self, loader=None, has_librosa=True):
        from planner import db as db
        self.addCleanup(setattr, db, "HAS_LIBROSA", db.HAS_LIBROSA)
        db.HAS_LIBROSA = has_librosa
        if loader is not None:
            fake = types.SimpleNamespace(load=loader)
            self.addCleanup(setattr, db, "librosa", getattr(db, "librosa", None))
            db.librosa = fake
        return db.probe_decode_backend(Path("song.mp3"))

    def test_no_librosa_is_reported_without_touching_the_file(self):
        from planner import db as db
        self.assertEqual(self._probe(has_librosa=False), db.PROBE_NO_LIBROSA)

    def test_a_decoder_that_works_says_nothing(self):
        self.assertIsNone(self._probe(loader=lambda *a, **kw: (None, 11025)))

    def test_a_missing_backend_is_told_apart_from_any_other_failure(self):
        from planner import db as db

        class NoBackendError(Exception):
            pass

        def _raise(*a, **kw):
            raise NoBackendError("no backend for song.mp3")

        self.assertEqual(self._probe(loader=_raise), db.PROBE_NO_BACKEND)

    def test_an_unrelated_failure_is_not_blamed_on_ffmpeg(self):
        from planner import db as db

        def _raise(*a, **kw):
            raise ValueError("truncated file")

        self.assertEqual(self._probe(loader=_raise), db.PROBE_FAILED)

    def test_stderr_is_handed_back_even_when_the_decoder_throws(self):
        # The probe redirects fd 2 to swallow the decoder's chatter; leaving it
        # pointing at the null device would silence the rest of the session.
        def _raise(*a, **kw):
            raise ValueError("boom")

        before = os.fstat(2)
        self._probe(loader=_raise)
        after = os.fstat(2)
        self.assertEqual((after.st_dev, after.st_ino, after.st_mode),
                         (before.st_dev, before.st_ino, before.st_mode))


class _Entry:
    def __init__(self, name):
        self.path = Path(name)


class _Store:
    """Fingerprints by filename, nothing cached yet."""

    def __init__(self):
        self.saved = 0

    def fingerprint(self, path):
        return path.name

    def has(self, fp, model):
        return False

    def save(self):
        self.saved += 1


class TooShortIsNotAnErrorTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(setattr, ae, "_embed_entry", ae._embed_entry)
        # The failure path logs a traceback on purpose — not into the test run.
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_short_file_is_skipped_not_failed(self):
        def fake(entry, model, store):
            if "swish" in entry.path.name:
                raise AudioTooShort("audio too short for a chroma descriptor")
            return True

        ae._embed_entry = fake
        computed, errors, first = ae.build_index(
            [_Entry("song.mp3"), _Entry("13_fx_transition_swish.mp3")],
            "chroma2dftm", _Store())
        self.assertEqual((computed, errors, first), (1, 0, None))

    def test_real_failures_still_count(self):
        def fake(entry, model, store):
            raise ValueError("model failed to load")

        ae._embed_entry = fake
        computed, errors, first = ae.build_index(
            [_Entry("song.mp3")], "chroma2dftm", _Store())
        self.assertEqual((computed, errors), (0, 1))
        self.assertIn("model failed to load", first)


class PassFailureReasonTest(unittest.TestCase):
    """Why a file could not be measured, and whether that is worth counting.

    A file the library still lists but that is gone from disk fails every pass,
    every time, and no rebuild will ever change that — so it is reported apart
    from the failures instead of colouring a run that did all it could.
    """

    @staticmethod
    def _pass(paths, ok_paths):
        from gui.workers import LibraryPass

        class _Cache:
            def save(self):
                pass

        class _Pass(LibraryPass):
            fail_hint = "ffmpeg could not read it"

            def todo(self):
                return list(self.paths)

            def measure(self, path):
                return path.name in ok_paths

        return _Pass(_Cache(), [Path(p) for p in paths])

    def _run(self, worker):
        reports, dones = [], []
        worker.report.connect(reports.append)
        worker.done.connect(lambda ok, err: dones.append((ok, err)))
        worker.run()          # in-thread: run() is the body, start() is not needed
        return reports[-1], dones[-1]

    def test_a_missing_file_is_skipped_not_counted_as_a_failure(self):
        worker = self._pass(["X:/gone.mp3"], ok_paths=set())
        rep, done = self._run(worker)
        self.assertEqual((rep["errors"], rep["skipped"]), (0, 1))
        self.assertEqual(done, (0, 0))
        self.assertEqual(rep["reasons"], {"not on disk any more": 1})

    def test_a_file_that_is_there_and_fails_is_a_failure_with_a_reason(self):
        here = Path(__file__)
        worker = self._pass([here], ok_paths=set())
        rep, done = self._run(worker)
        self.assertEqual((rep["errors"], rep["skipped"]), (1, 0))
        self.assertEqual(done, (0, 1))
        self.assertEqual(rep["reasons"], {"ffmpeg could not read it": 1})

    def test_a_clean_run_reports_nothing_to_explain(self):
        here = Path(__file__)
        worker = self._pass([here], ok_paths={here.name})
        rep, done = self._run(worker)
        self.assertEqual((rep["ok"], rep["errors"], rep["skipped"]), (1, 0, 0))
        self.assertEqual(rep["reasons"], {})
        self.assertEqual(done, (1, 0))

    def test_every_pass_names_its_own_likeliest_reason(self):
        from gui.workers import (AudioFpAnalyzer, LoudnessAnalyzer,
                                 SilenceAnalyzer, VocalShareAnalyzer)
        for cls in (AudioFpAnalyzer, LoudnessAnalyzer, SilenceAnalyzer,
                    VocalShareAnalyzer):
            with self.subTest(cls.__name__):
                self.assertTrue(cls.fail_hint)


class BuildAllReasonTest(unittest.TestCase):
    """The closing report says WHY a step failed, and what it could never do."""

    def setUp(self):
        os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                              tempfile.mkdtemp(prefix="dp_allc_"))
        from gui import main_allcache as gmg
        self.gmg = gmg
        self.boxes = _Boxes()
        self.addCleanup(setattr, gmg, "QMessageBox", gmg.QMessageBox)
        gmg.QMessageBox = self.boxes
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

    def test_the_reason_rides_along_into_the_report(self):
        win = _report_window(self.gmg, ["silences"])
        win._allcache_note_report(
            "🔇 silences", {"ok": 10, "errors": 2, "skipped": 0,
                            "reasons": {"ffmpeg could not read it": 2}})
        win._allcache_step_done("🔇 silences", 10, 2)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "warning")
        self.assertIn("2 file(s) failed (ffmpeg could not read it)", text)

    def test_several_reasons_are_led_by_the_commonest(self):
        win = _report_window(self.gmg, ["librosa"])
        win._allcache_note_report(
            "librosa", {"ok": 1, "errors": 4, "skipped": 0,
                        "reasons": {"no backend": 3, "odd sample rate": 1}})
        win._allcache_step_done("librosa", 1, 4)
        _kind, _title, text = self.boxes.calls[-1]
        self.assertIn("mostly: no backend", text)

    def test_files_that_are_gone_do_not_make_a_run_look_broken(self):
        win = _report_window(self.gmg, ["loudness"])
        win._allcache_note_report(
            "📊 loudness", {"ok": 300, "errors": 0, "skipped": 4,
                            "reasons": {"not on disk any more": 4}})
        win._allcache_step_done("📊 loudness", 300, 0)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "information")            # NOT a warning
        self.assertIn("All caches are built", text)
        self.assertIn("4 file(s) skipped", text)         # …but said out loud

    def test_a_step_with_both_names_them_apart(self):
        win = _report_window(self.gmg, ["loudness"])
        win._allcache_note_report(
            "📊 loudness", {"ok": 5, "errors": 2, "skipped": 3,
                            "reasons": {"ffmpeg could not read it": 2,
                                        "not on disk any more": 3}})
        win._allcache_step_done("📊 loudness", 5, 2)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "warning")
        self.assertIn("2 file(s) failed", text)
        self.assertIn("3 file(s) skipped", text)

    def test_a_step_that_never_reported_still_closes_cleanly(self):
        win = _report_window(self.gmg, ["librosa"])
        win._allcache_step_done("librosa", 7, 0)
        kind, _title, text = self.boxes.calls[-1]
        self.assertEqual(kind, "information")
        self.assertNotIn("skipped", text)

    def test_a_step_that_died_outright_leaves_the_labels_current(self):
        """The 🔊 gate follows the loudness cache — an aborted step used to
        leave it saying whatever it said before the build."""
        win = _report_window(self.gmg, ["loudness"])
        win._allcache_embedding_error("ffmpeg is not installed")
        self.assertEqual(win.synced, 1)
        self.assertIsNone(win._allcache)
        self.assertEqual(self.boxes.calls[-1][0], "critical")


if __name__ == "__main__":
    unittest.main()
