"""🧳 USB export offers the 📦 venue pack as a button of its own.

Run:  py -m unittest tests.gui.test_usb_export_venue_pack -v

The venue pack (settings, decks, cartwall, the music if wanted) was only
reachable from ⚙ Settings, while taking things to the venue starts at the
USB export. Chosen there, it runs the same export as the Settings button;
the Settings button stays. No box beside the others: the pack is no bundle, so
it combines with none of them.
"""
import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QPushButton

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

    def test_the_button_row_lines_up_with_the_row_above(self):
        """The Windows style pushed a QDialogButtonBox 6 px in from the left."""
        dlg = self.dialog(n_decks=2)
        dlg.show()
        self.app.processEvents()
        left = lambda b: b.mapTo(dlg, b.rect().topLeft()).x()
        add = next(b for b in dlg.findChildren(QPushButton)
                   if b.text().endswith("Add files…"))
        self.assertEqual(left(dlg._ok), left(add))
        self.assertEqual(dlg.findChildren(QDialogButtonBox), [])

    def test_the_dialog_offers_the_venue_pack(self):
        dlg = self.dialog(n_decks=2)
        self.assertFalse(dlg.venue_pack())
        dlg._venue.click()
        self.assertTrue(dlg.venue_pack())
        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)

    def test_it_needs_no_open_playlist(self):
        """The pack carries the settings and the cartwall even with every deck empty."""
        dlg = self.dialog()
        self.assertFalse(dlg._ok.isEnabled())
        self.assertTrue(dlg._venue.isEnabled())

    def test_a_plain_export_is_no_venue_pack(self):
        dlg = self.dialog(n_decks=2)
        dlg._ok.click()
        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)
        self.assertFalse(dlg.venue_pack())

    def test_choosing_it_runs_the_venue_pack_export(self):
        host = mock.Mock()
        host._deckset.decks = []
        host._deckset.day_decks = []
        host._deckset.wishlists = []
        host._deckset.warmup_table._row_meta.entries.return_value = []
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.venue_pack.return_value = True
        with mock.patch.object(main_export, "UsbExportDialog", return_value=ask):
            main_export.ExportMixin._export_bundle(host)
        host._export_venue_pack.assert_called_once_with()
        host._pick_bundle_dir.assert_not_called()
        host._write_bundle.assert_not_called()


if __name__ == "__main__":
    unittest.main()
