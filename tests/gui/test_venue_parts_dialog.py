"""📥 The venue pack import asks which parts of the pack to take over.

Run:  py -m unittest tests.gui.test_venue_parts_dialog -v
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox

from gui.dialogs.venue_parts_dialog import PackPartsDialog, ask_pack_parts
from tests.qt_test_support import reap_widget

_NAMES = ["gui_settings.json", "autosave_playlist.json", "cartwall.json"]


class PackPartsDialogTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, names=_NAMES):
        dlg = PackPartsDialog(None, names)
        self.addCleanup(reap_widget, dlg)
        return dlg

    def ok(self, dlg):
        return dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok)

    def test_everything_is_ticked_to_begin_with(self):
        self.assertEqual(self.dialog().chosen(), _NAMES)

    def test_an_unticked_part_is_left_out_and_the_order_kept(self):
        dlg = self.dialog()
        dlg._ticks["autosave_playlist.json"].setChecked(False)
        self.assertEqual(dlg.chosen(), ["gui_settings.json", "cartwall.json"])

    def test_ok_needs_at_least_one_part(self):
        dlg = self.dialog()
        for chk in dlg._ticks.values():
            chk.setChecked(False)
        self.assertFalse(self.ok(dlg).isEnabled())
        dlg._ticks["cartwall.json"].setChecked(True)
        self.assertTrue(self.ok(dlg).isEnabled())

    def test_cancel_answers_none(self):
        from unittest import mock
        with mock.patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            self.assertIsNone(ask_pack_parts(None, _NAMES))

    def test_ok_answers_the_ticked_parts(self):
        from unittest import mock
        with mock.patch.object(QDialog, "exec", return_value=QDialog.DialogCode.Accepted):
            self.assertEqual(ask_pack_parts(None, _NAMES), _NAMES)


if __name__ == "__main__":
    unittest.main()
