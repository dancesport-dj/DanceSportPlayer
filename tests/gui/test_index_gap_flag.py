#!/usr/bin/env python3
"""When the status block's 🧱 shortcut is allowed to appear.

Run:  .venv/Scripts/python.exe -m unittest tests.gui.test_index_gap_flag -v

The button starts "Build ALL caches", and that build can only be pointed at a
library that is loaded — so it may only show for a gap in the FAVORITES
library. Two things would otherwise put a permanent button on screen that no
click can ever clear: a half-built repository index, and a model whose backend
is not installed at all (OpenL3 without TensorFlow, say).
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_gapflag_"))

import planner.db  # noqa: E402
from gui.index_summary import index_summary  # noqa: E402
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
    """Answers the ffmpeg-measured coverage for a chosen set of paths."""

    def __init__(self, measured=None):
        self._measured = set(measured) if measured is not None else None

    def _hit(self, paths):
        if self._measured is None:
            return len(paths)
        return sum(1 for p in paths if Path(p).name in self._measured)

    def coverage_counts(self, paths, audio_fps=None):
        n = self._hit(paths)
        return {"audiofp": n, "loudness": n, "silences": n, "pd": n}

    def audio_fp_keys(self):
        return set()

    def known_fingerprint(self, path):
        return f"FP:{Path(path).name}"

    def vocal_share_count(self):
        return 0


class _Store:
    """The embedding store, as a pair of fingerprint sets."""

    def __init__(self, ol3, chroma):
        self._fps = {"openl3": set(ol3), "chroma2dftm": set(chroma)}

    def fps(self, model):
        return self._fps.get(model, set())


def _summary(lib, cache=None, store=None, global_lib=None):
    return index_summary(cache if cache is not None else _Cache(), store,
                         lib, global_lib)


class FavoritesGapFlagTest(unittest.TestCase):

    def setUp(self):
        # No global library loaded → the summary would ask the real DB how big
        # the repository index is. Keep the test off the disk.
        self._real_count = planner.db.global_index_count
        planner.db.global_index_count = lambda: 0
        self.addCleanup(setattr, planner.db, "global_index_count", self._real_count)

    def test_a_fully_analyzed_favorites_library_needs_no_build(self):
        summ = _summary(_Lib([_entry("A"), _entry("B")]))
        self.assertFalse(summ["favorites_gap"])

    def test_a_missing_librosa_vector_is_a_gap(self):
        summ = _summary(_Lib([_entry("A"), _entry("B", analyzed=False)]))
        self.assertTrue(summ["favorites_gap"])

    def test_a_missing_loudness_measurement_is_a_gap(self):
        summ = _summary(_Lib([_entry("A"), _entry("B")]),
                        cache=_Cache(measured={"A.mp3"}))
        self.assertTrue(summ["favorites_gap"])

    def test_only_the_favorites_library_counts(self):
        """A half-built repository index is real, but no button here can fix it."""
        summ = _summary(_Lib([_entry("A")]),
                        global_lib=_Lib([_entry("R1"), _entry("R2", analyzed=False)]))
        self.assertTrue(summ["librosa"].count("/") == 2)  # both shown
        self.assertFalse(summ["favorites_gap"])

    def test_the_fingerprint_pass_has_a_line_of_its_own(self):
        """🔗 is the FIRST thing 🧱 builds, and had no counter at all — so the
        one step that always has work on an old library showed no progress."""
        summ = _summary(_Lib([_entry("A"), _entry("B")]),
                        cache=_Cache(measured={"A.mp3"}))
        self.assertEqual(summ["audiofp"], "Favorites 1/2")

    def test_a_missing_fingerprint_is_a_gap(self):
        summ = _summary(_Lib([_entry("A"), _entry("B")]),
                        cache=_Cache(measured={"A.mp3"}))
        self.assertTrue(summ["favorites_gap"])

    def test_an_uninstalled_model_is_not_a_gap(self):
        """OpenL3 without TensorFlow: 0/2 forever, and no build can close it."""
        self._patch_availability(openl3=False, chroma=False)
        summ = _summary(_Lib([_entry("A"), _entry("B")]), store=_Store([], []))
        self.assertFalse(summ["favorites_gap"])

    def test_an_installed_model_that_is_behind_is_a_gap(self):
        self._patch_availability(openl3=False, chroma=True)
        summ = _summary(_Lib([_entry("A"), _entry("B")]),
                        store=_Store([], ["FP:A.mp3"]))
        self.assertTrue(summ["favorites_gap"])

    def _patch_availability(self, openl3: bool, chroma: bool):
        from planner import embeddings as ae
        for name, val in (("openl3_available", openl3), ("chroma_available", chroma)):
            real = getattr(ae, name)
            setattr(ae, name, lambda v=val: v)
            self.addCleanup(setattr, ae, name, real)


if __name__ == "__main__":
    unittest.main(verbosity=2)
