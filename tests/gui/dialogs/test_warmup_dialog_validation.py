"""Practice dialog: a missing input is reported with the dialog still open (#77)."""
import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QRadioButton

from gui.dialogs import M3uDropDialog
from gui.dialogs.warmup_dialog import ask_warmup_options


class WarmupValidationTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_an_empty_m3u_path_keeps_the_dialog_and_its_choices(self):
        store = {}
        calls = []

        def fake_exec(dlg):
            calls.append(1)
            radios = {rb.text(): rb for rb in dlg.findChildren(QRadioButton)}
            if len(calls) == 1:
                radios["An .m3u playlist file"].setChecked(True)   # path left empty
            else:
                radios["⭐  Favorites"].setChecked(True)
            return QDialog.DialogCode.Accepted

        with mock.patch.object(M3uDropDialog, "exec", fake_exec), \
                mock.patch.object(QMessageBox, "warning") as warn, \
                mock.patch("gui.dialogs.warmup_dialog.load_settings", lambda: store), \
                mock.patch("gui.dialogs.warmup_dialog.save_settings", store.update):
            opts = ask_warmup_options(None, [], "", ())
        self.assertEqual(len(calls), 2)          # it came back instead of losing the settings
        warn.assert_called_once()
        self.assertEqual(opts["source"], "library")


if __name__ == "__main__":
    unittest.main()
