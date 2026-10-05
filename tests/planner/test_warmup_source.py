#!/usr/bin/env python3
"""Which pool the 🤸 Eintanzen / Party "⭐ Favorites" source hands the builder.

Run:  py -m unittest tests.planner.test_warmup_source -v

Two promises are pinned here, because both are invisible from the dialog:

* "Favorites" means the library scanned from `library_dir` — `self._lib`. The
  global repository (`self._global_lib`, built for similarity search only) must
  never leak into a generated list.
* A track filed under a library category (duplicates / wrong tempo / anthems /
  background / seasonal) lives in that same folder but is not tournament music.
  `class_warmup_pool` drops it; the party build does not, so the source has to.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR",
                      tempfile.mkdtemp(prefix="dp_warmsrc_"))

from gui import main_generate as gen  # noqa: E402
from gui.main_dupes import DuplicateCheckMixin  # noqa: E402
from planner.models import MusicEntry  # noqa: E402


def _entry(name, folder="lateincd/SA"):
    return MusicEntry(path=Path(f"C:/lib/{folder}/{name}.mp3"),
                      title=name, dance="SA", bpm=51)


class _Signal:
    def connect(self, *_a, **_k):
        pass


class _FakeBuilder:
    """Stands in for WarmupBuilder — remembers the pool it was handed."""
    last = None

    def __init__(self, src, mode, params, parent=None):
        _FakeBuilder.last = list(src)
        self.progress = self.done = self.error = self.finished = _Signal()

    def start(self):
        pass


class _FakeBusy:
    def __init__(self, *_a, **_k):
        pass

    def show_after(self, *_a):
        pass

    def finish(self, *_a):
        pass


class _Bar:
    def showMessage(self, *_a):
        pass


class _Win:
    """The MainWindow reduced to what `_generate_warmup` reads."""

    def __init__(self, entries, opts, planned=()):
        self._lib = type("L", (), {"entries": entries})()
        # A loaded global repository that must stay out of the result.
        self._global_lib = type("L", (), {
            "entries": [_entry("REPO ONLY", "F:/repo")]})()
        self._cache = None
        self._wishlists = []
        self._opts = opts
        self._planned = list(planned)

    _generate_warmup = gen.GenerateMixin._generate_warmup
    _deck_dedup_index = DuplicateCheckMixin._deck_dedup_index

    def _ask_warmup_options(self):
        return self._opts

    def _visible_deck_tables(self):
        # One open deck holding the planned tracks.
        meta = type("M", (), {"entries": lambda _s: list(self._planned)})()
        return [type("D", (), {"_row_meta": meta})()]

    def statusBar(self):
        return _Bar()

    # the slots the builder is wired to — never reached, the fake never emits
    def _on_warmup_done(self, *_a):
        pass

    def _on_warmup_error(self, *_a):
        pass


_PARTY = {"source": "library", "unused_only": False, "mode": "etds",
          "etds": {}, "m3u_path": ""}


class WarmupSourceTest(unittest.TestCase):

    def setUp(self):
        self._real_builder = gen.WarmupBuilder
        self._real_busy = gen.BusyDialog
        gen.WarmupBuilder = _FakeBuilder
        gen.BusyDialog = _FakeBusy
        _FakeBuilder.last = None
        self.addCleanup(self._restore)

    def _restore(self):
        gen.WarmupBuilder = self._real_builder
        gen.BusyDialog = self._real_busy

    @staticmethod
    def _run(entries, opts=None, planned=()):
        _Win(entries, dict(opts or _PARTY), planned)._generate_warmup()
        return [e.title for e in (_FakeBuilder.last or [])]

    def test_the_pool_is_the_favorites_library(self):
        got = self._run([_entry("SA 1"), _entry("SA 2")])
        self.assertEqual(got, ["SA 1", "SA 2"])
        self.assertNotIn("REPO ONLY", got)

    def test_categorised_tracks_stay_out(self):
        """They sit inside the Favorites folder, but they are not favorites."""
        entries = [_entry("SA 1"),
                   _entry("SA raw", "lateincd/SA/originale"),
                   _entry("SA slow", "lateincd/SA/nicht turnier"),
                   _entry("Anthem", "hymnen"),
                   _entry("Bed", "musikbett")]
        self.assertEqual(self._run(entries), ["SA 1"])

    def test_a_christmas_flag_alone_is_enough(self):
        xmas = _entry("SA xmas")
        xmas.is_xmas = True
        self.assertEqual(self._run([_entry("SA 1"), xmas]), ["SA 1"])

    def test_the_class_warmup_uses_the_same_pool(self):
        opts = {"source": "library", "unused_only": False, "mode": "class",
                "style": "Latin", "dance_class": "S", "max_tracks": 20,
                "fresh_ratio": 0.3, "relax": True, "m3u_path": ""}
        got = self._run([_entry("SA 1"), _entry("SA dup", "lateincd/SA/orig")],
                        opts)
        self.assertEqual(got, ["SA 1"])

    def test_unused_only_leaves_out_what_a_deck_plans(self):
        """Matched by path, whatever its letter case: the deck index is
        lower-cased, a library path keeps its capitals (`C:`, `SA`), and
        with no fingerprint on record the path is all there is to go on."""
        planned = _entry("SA 1")
        got = self._run([planned, _entry("SA 2")],
                        dict(_PARTY, unused_only=True), planned=[planned])
        self.assertEqual(got, ["SA 2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
