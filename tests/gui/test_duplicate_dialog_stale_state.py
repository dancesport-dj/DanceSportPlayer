"""Check-duplicates dialog: stale preview button and stale compare (#73, #74)."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shiboken6
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QLabel

from gui.dialogs.duplicate_dialog import DuplicateResolveDialog
from tests.qt_test_support import reap_widget


class _Worker(QObject):
    progress = Signal(int, int)
    done = Signal(dict)
    failed = Signal(str)
    finished = Signal()

    def start(self):
        pass


class DuplicateDialogStaleStateTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make(self, **kw):
        self.played = []
        dlg = DuplicateResolveDialog({"within": [], "cross": []}, None,
                                     lambda e: None, play_cb=self.played.append, **kw)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def test_a_preview_whose_button_was_deleted_still_stops(self):
        """#73: setText on the dead button raised, so the music kept playing."""
        dlg = self.make()
        btn = dlg._make_play_btn("x.mp3")
        dlg._toggle_play("x.mp3", btn)
        shiboken6.delete(btn)
        dlg._stop_preview()
        self.assertEqual(self.played, [Path("x.mp3"), None])

    def test_choosing_a_replacement_stops_the_title_being_previewed(self):
        """Tier 1 #4: the old title kept playing under the picker and its ■ stayed,
        so the new title needed two clicks."""
        self.played = []
        seen = []
        dlg = DuplicateResolveDialog({"within": [], "cross": []}, None,
                                     lambda e: seen.append(list(self.played)),
                                     play_cb=self.played.append)
        self.addCleanup(reap_widget, dlg)
        btn = dlg._make_play_btn("old.mp3")
        dlg._toggle_play("old.mp3", btn)
        label = QLabel()
        dlg._choose_replacement({"occ": {"entry": None}, "replacement": None,
                                 "repl_lbl": label, "combo": None})
        self.assertEqual(self.played, [Path("old.mp3"), None])
        self.assertEqual(btn.text(), "▶")
        self.assertEqual(seen, [[Path("old.mp3"), None]])

    def test_a_result_of_an_older_comparison_is_ignored(self):
        """#74: it showed a result for a reference that was swapped meanwhile."""
        workers = []

        def factory(ref, tour):
            workers.append(_Worker())
            return workers[-1]

        dlg = self.make(ref_clean_factory=factory)
        dlg._ref_path = Path("ref.m3u")
        dlg._ref_tour_files.paths = lambda: ["t.m3u"]
        dlg._on_ref_compare()
        dlg._ref_path = Path("other.m3u")
        dlg._on_ref_inputs_changed()
        workers[0].done.emit({"removed": [], "kept_blocks": [], "ref_total": 1})
        self.assertIsNone(dlg._ref_result)


if __name__ == "__main__":
    unittest.main()
