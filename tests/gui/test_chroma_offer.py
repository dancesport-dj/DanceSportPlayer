r"""🔁 Check duplicates offers to read Chromaprints first, only when it can help.

Run:  .venv\Scripts\python.exe -m unittest tests.gui.test_chroma_offer -v
"""
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from gui.window import main_dupes
from gui.window.main_dupes import DuplicateCheckMixin
from tests.qt_test_support import reap_widget


class _Table:
    def __init__(self, paths):
        self._row_meta = SimpleNamespace(numbered=lambda: [
            (i, SimpleNamespace(entry=SimpleNamespace(path=Path(p))))
            for i, p in enumerate(paths)])


class _Cache:
    def __init__(self, have=()):
        self.have = set(have)

    def get_chroma(self, path, touch_disk=True):
        return object() if str(path) in self.have else None


class _Win(QWidget, DuplicateCheckMixin):
    def __init__(self, cache, paths):
        super().__init__()
        self._library = SimpleNamespace(cache=cache)
        self._paths = paths
        self.passes = []

    def _dup_check_tables(self):
        return [_Table(self._paths)]

    def _run_library_pass(self, worker, *a, **kw):
        self.passes.append((worker, kw))


class OfferTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def win(self, cache, paths):
        w = _Win(cache, paths)
        self.addCleanup(reap_widget, w)
        return w

    def ask(self, w, answer, fpcalc="fpcalc"):
        with mock.patch.object(main_dupes, "find_fpcalc", return_value=fpcalc), \
                mock.patch.object(main_dupes.QMessageBox, "question",
                                  return_value=answer) as q:
            return w._offer_chroma_pass(), q

    def test_yes_starts_the_pass_for_the_missing_tracks_only(self):
        w = self.win(_Cache(have={str(Path("a.mp3"))}), ["a.mp3", "b.mp3", "b.mp3"])
        started, _q = self.ask(w, QMessageBox.StandardButton.Yes)
        self.assertTrue(started)
        self.assertEqual(w.passes[0][0].paths, [Path("b.mp3")])

    def test_no_means_the_check_goes_on(self):
        w = self.win(_Cache(), ["a.mp3"])
        started, _q = self.ask(w, QMessageBox.StandardButton.No)
        self.assertFalse(started)
        self.assertEqual(w.passes, [])

    def test_nothing_missing_asks_nothing(self):
        w = self.win(_Cache(have={str(Path("a.mp3"))}), ["a.mp3"])
        started, q = self.ask(w, QMessageBox.StandardButton.Yes)
        self.assertFalse(started)
        q.assert_not_called()

    def test_without_fpcalc_asks_nothing(self):
        w = self.win(_Cache(), ["a.mp3"])
        started, q = self.ask(w, QMessageBox.StandardButton.Yes, fpcalc=None)
        self.assertFalse(started)
        q.assert_not_called()


if __name__ == "__main__":
    unittest.main()
