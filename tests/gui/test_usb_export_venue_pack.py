"""🧳 USB export offers the 📦 venue pack as one more choice.

Run:  py -m unittest tests.gui.test_usb_export_venue_pack -v

The venue pack (settings, decks, cartwall, the music if wanted) was only
reachable from ⚙ Settings, while taking things to the venue starts at the
USB export. Chosen there, it runs the same export as the Settings button;
the Settings button stays.
"""
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication, QDialog

from gui.dialogs import UsbExportDialog
from gui.window import main_export


class UsbExportVenuePackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def dialog(self, **kw):
        dlg = UsbExportDialog(None, **kw)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_the_dialog_offers_the_venue_pack(self):
        dlg = self.dialog(n_decks=2)
        self.assertFalse(dlg._rb_venue.isChecked())
        dlg._rb_venue.setChecked(True)
        self.assertEqual(dlg.mode(), "venue")
        self.assertTrue(dlg._ok.isEnabled())

    def test_it_needs_no_open_playlist(self):
        """The pack carries the settings and the cartwall even with every deck empty."""
        dlg = self.dialog()
        self.assertTrue(dlg._rb_venue.isEnabled())
        dlg._rb_venue.setChecked(True)
        self.assertTrue(dlg._ok.isEnabled())

    def test_choosing_it_runs_the_venue_pack_export(self):
        host = mock.Mock()
        host._deckset.decks = []
        host._deckset.day_decks = []
        host._grid.deck_tabs.currentIndex.return_value = 0
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.mode.return_value = "venue"
        with mock.patch.object(main_export, "UsbExportDialog", return_value=ask):
            main_export.ExportMixin._export_bundle(host)
        host._export_venue_pack.assert_called_once_with()
        host._pick_bundle_dir.assert_not_called()
        host._write_bundle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
