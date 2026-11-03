"""📤 The reference-base export (#45, #46)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("DANCEPLAYLIST_STATE_DIR", tempfile.mkdtemp(prefix="dp_dup_export_"))

from PySide6.QtWidgets import QApplication, QMessageBox

from gui.dialogs import duplicate_dialog as dd
from tests.qt_test_support import reap_widget


class ReferenceExportTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_dup_export_"))
        self.dlg = dd.DuplicateResolveDialog({}, None, lambda e: None, ref_clean_factory=lambda: None)
        self.addCleanup(reap_widget, self.dlg)
        ref = self.dir / "ref.m3u"
        self.dlg._ref_result = {
            "ref_path": str(ref),
            "kept_blocks": [{"path": self.dir / "a LW.mp3", "raw": ["a LW.mp3"], "title": "a"}],
            "removed": [object(), object()]}

    def export(self, name):
        out = str(self.dir / name)
        with (mock.patch.object(dd.QFileDialog, "getSaveFileName", return_value=(out, "")),
              mock.patch.object(dd.QMessageBox, "question",
                                return_value=QMessageBox.StandardButton.No) as ask,
              mock.patch.object(dd.QMessageBox, "information") as info):
            self.dlg._on_ref_export_now()
        return ask, info

    def test_a_second_export_still_reports_the_removed_duplicates(self):
        _ask, info = self.export("one.m3u")
        self.assertIn("2 hard duplicate", info.call_args.args[2])
        _ask, info = self.export("two.m3u")
        self.assertIn("2 hard duplicate", info.call_args.args[2])

    def test_the_legend_names_the_codes_the_sort_uses(self):
        ask, _info = self.export("one.m3u")
        legend = ask.call_args.args[2]
        for code in dd.TOURNAMENT_DANCE_ORDER:
            self.assertIn(code, legend)
        self.assertNotIn("SB", legend)


if __name__ == "__main__":
    unittest.main()
