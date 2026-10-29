"""🧳 USB export names its folder after the tournament.

Run:  py -m unittest tests.gui.test_usb_export_folder_name -v

The bundle always went into a dated ``Turnier_<date>`` folder. Now the name
is guessed from the folder the exported playlists were loaded from or saved
to, which for a tournament is its own folder. Picked a drive's top level, the
export asks what to call the folder, with that guess filled in. Picked a sub
folder, it asks whether to make a tournament folder there at all, or write
straight into the folder picked. Written straight in, Cancel takes back only
what it wrote, never the folder itself.
"""
import shutil
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox

from gui.dialogs import UsbBundleFolderDialog
from gui.window import main_export
from gui.window.main_export import ExportMixin, bundle_name_guess
from planner.config import playlist_dir, set_playlist_dir
from tests.gui.window.test_bundle_export_thread import _FakeBusy
from tests.qt_test_support import reap_widget

_app = QApplication.instance() or QApplication([])
DATED = f"Turnier_{date.today().isoformat()}"
ROOT = playlist_dir()


class GuessTest(unittest.TestCase):
    def setUp(self):
        # A window built earlier in the process repoints the playlist folder
        # from its settings and leaves it there; the guesses are about ROOT.
        self.addCleanup(set_playlist_dir, playlist_dir())
        set_playlist_dir(ROOT)

    def test_the_folder_the_playlist_lies_in(self):
        self.assertEqual(
            bundle_name_guess([ROOT / Path("2026/Gala Hamburg/final.m3u")]),
            "Gala Hamburg")

    def test_sibling_folders_name_the_one_above_them(self):
        self.assertEqual(bundle_name_guess([
            ROOT / Path("2026/Gala Hamburg/Sen/a.m3u"),
            ROOT / Path("2026/Gala Hamburg/Hgr/b.m3u")]), "Gala Hamburg")

    def test_unrelated_folders_take_the_one_most_lists_lie_in(self):
        self.assertEqual(bundle_name_guess([
            ROOT / Path("2026/Gala/a.m3u"),
            ROOT / Path("2025/Cup/b.m3u"),
            ROOT / Path("2025/Cup/c.m3u")]), "Cup")

    def test_the_apps_own_output_folders_name_nothing(self):
        out = main_export.OUTPUT_DIR
        self.assertEqual(bundle_name_guess([out / "a.m3u"]), DATED)
        self.assertEqual(bundle_name_guess([out.parent / "wishlists" / "w.m3u"]),
                         DATED)

    def test_a_year_folder_names_nothing(self):
        self.assertEqual(bundle_name_guess([
            ROOT / Path("2026/Gala/a.m3u"),
            ROOT / Path("2026/Cup/b.m3u")]), "Gala")

    def test_the_playlist_root_itself_names_nothing(self):
        self.assertEqual(bundle_name_guess([ROOT / "a.m3u"]), DATED)

    def test_no_file_at_all_is_the_dated_name(self):
        self.assertEqual(bundle_name_guess([None]), DATED)
        self.assertEqual(bundle_name_guess([Path("E:/a.m3u")]), DATED)


class DialogTest(unittest.TestCase):
    def dialog(self, at_top):
        dlg = UsbBundleFolderDialog(None, Path("E:/Musik"), "Gala", at_top)
        self.addCleanup(dlg.deleteLater)
        return dlg

    def test_the_guess_is_filled_in(self):
        self.assertEqual(self.dialog(True).name(), "Gala")

    def test_at_the_top_there_is_no_straight_in(self):
        self.assertIsNone(self.dialog(True)._into)

    def test_in_a_sub_folder_straight_in_is_offered(self):
        dlg = self.dialog(False)
        dlg._into.click()
        self.assertTrue(dlg.into_root())
        self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)

    def test_creating_is_not_straight_in(self):
        dlg = self.dialog(False)
        dlg._create.click()
        self.assertFalse(dlg.into_root())

    def test_enter_in_the_name_creates_the_folder(self):
        # Marcel: typed the name, hit Enter, and the export was cancelled.
        for at_top in (True, False):
            dlg = self.dialog(at_top)
            dlg.show()
            dlg._edit.setFocus()
            QTest.keyClick(dlg._edit, Qt.Key.Key_Return)
            self.assertEqual(dlg.result(), QDialog.DialogCode.Accepted)
            self.assertFalse(dlg.into_root())

    def test_no_name_no_folder(self):
        dlg = self.dialog(True)
        dlg._edit.setText("  ")
        self.assertFalse(dlg._create.isEnabled())


class PickTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_bundle_name_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.host = mock.Mock()

    def pick(self, into=False, name="Gala", mount=False):
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.into_root.return_value = into
        ask.name.return_value = name
        with mock.patch.object(main_export.QFileDialog, "getExistingDirectory",
                               return_value=str(self.dir)), \
             mock.patch.object(main_export.os.path, "ismount", return_value=mount), \
             mock.patch.object(main_export, "UsbBundleFolderDialog",
                               return_value=ask) as dlg_cls:
            got = ExportMixin._pick_bundle_dir(self.host, "Gala")
        return got, dlg_cls.call_args.args

    def test_a_sub_folder_asks_with_the_guess(self):
        _got, args = self.pick()
        self.assertEqual(args[1:], (self.dir, "Gala", False))

    def test_a_drives_top_level_asks_for_the_name(self):
        _got, args = self.pick(mount=True)
        self.assertTrue(args[3])

    def test_the_named_folder_is_made(self):
        got, _args = self.pick(name="Gala Hamburg")
        self.assertEqual(got, (self.dir / "Gala Hamburg", True))
        self.assertTrue((self.dir / "Gala Hamburg").is_dir())

    def test_a_typed_name_keeps_its_spaces_but_no_forbidden_sign(self):
        got, _args = self.pick(name="Gala: Hamburg?")
        self.assertEqual(got[0].name, "Gala_ Hamburg_")

    def test_straight_in_writes_into_the_folder_picked(self):
        got, _args = self.pick(into=True)
        self.assertEqual(got, (self.dir, False))
        self.assertEqual(list(self.dir.iterdir()), [])


class _Box:
    """QMessageBox stand-in: records the text and buttons, clicks `click`."""
    Icon = QMessageBox.Icon
    ButtonRole = QMessageBox.ButtonRole
    StandardButton = QMessageBox.StandardButton
    click = "Replace"
    last = None
    errors: list = []

    def __init__(self, _parent):
        self.text = ""
        self.buttons = {}
        _Box.last = self

    def setWindowTitle(self, _t): pass
    def setIcon(self, _i): pass
    def setDefaultButton(self, _b): pass
    def exec(self): pass

    def setText(self, text):
        self.text = text

    def addButton(self, label, _role=None):
        self.buttons[label] = object()
        return self.buttons[label]

    def clickedButton(self):
        return self.buttons.get(_Box.click)

    @staticmethod
    def critical(_parent, _title, text):
        _Box.errors.append(text)


class ReplaceTest(unittest.TestCase):
    """A folder of that name already there: Replace only an older export,
    say where it is, and a locked file ends in a message, not a crash."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_bundle_replace_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.gala = self.dir / "Gala"
        self.gala.mkdir()
        _Box.click = "Replace"
        _Box.errors = []

    def pick(self):
        ask = mock.Mock()
        ask.exec.return_value = QDialog.DialogCode.Accepted
        ask.into_root.return_value = False
        ask.name.return_value = "Gala"
        with mock.patch.object(main_export.QFileDialog, "getExistingDirectory",
                               return_value=str(self.dir)), \
             mock.patch.object(main_export.os.path, "ismount", return_value=False), \
             mock.patch.object(main_export, "UsbBundleFolderDialog", return_value=ask), \
             mock.patch.object(main_export, "QMessageBox", _Box):
            return ExportMixin._pick_bundle_dir(mock.Mock(), "Gala")

    def an_older_export(self):
        (self.gala / "Final").mkdir()
        (self.gala / "Final" / "Final.m3u8").write_text("#EXTM3U\n", encoding="utf-8")
        (self.gala / "Final" / "01 a.mp3").write_bytes(b"x")

    def test_the_question_names_the_full_path(self):
        self.an_older_export()
        self.pick()
        self.assertIn(str(self.gala), _Box.last.text)

    def test_an_older_export_is_replaced(self):
        self.an_older_export()
        self.assertEqual(self.pick(), (self.gala, True))
        self.assertEqual(list(self.gala.iterdir()), [])

    def test_a_folder_that_is_no_export_cannot_be_replaced(self):
        (self.gala / "taxes.xlsx").write_bytes(b"x")
        self.assertIsNone(self.pick())
        self.assertNotIn("Replace", _Box.last.buttons)
        self.assertTrue((self.gala / "taxes.xlsx").exists())

    def test_a_folder_that_is_no_export_can_still_be_kept_beside(self):
        (self.gala / "Final").mkdir()
        _Box.click = "Keep both"
        self.assertEqual(self.pick(), (self.dir / "Gala_2", True))
        self.assertTrue((self.gala / "Final").is_dir())

    def test_a_locked_file_ends_in_a_message(self):
        self.an_older_export()
        with mock.patch.object(main_export.shutil, "rmtree",
                               side_effect=PermissionError("in use")):
            self.assertIsNone(self.pick())
        self.assertEqual(len(_Box.errors), 1)
        self.assertIn(str(self.gala), _Box.errors[0])
        self.assertIn("in use", _Box.errors[0])

    def test_a_folder_that_cannot_be_made_ends_in_a_message(self):
        _Box.click = "Keep both"
        with mock.patch.object(Path, "mkdir", side_effect=PermissionError("read-only")):
            self.assertIsNone(self.pick())
        self.assertEqual(len(_Box.errors), 1)
        self.assertIn("read-only", _Box.errors[0])


class StraightInTest(unittest.TestCase):
    """Written into a folder the user picked, nothing of theirs is touched."""

    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="dp_bundle_in_"))
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.host = QMainWindow()
        self.addCleanup(reap_widget, self.host)
        self.writing = threading.Event()
        self.gate = None
        no_box = mock.patch.object(QMessageBox, "exec", return_value=0)
        no_box.start()
        self.addCleanup(no_box.stop)

    def _write(self, out: Path) -> Path:
        self.writing.set()
        out.write_text("#EXTM3U\n", encoding="utf-8")
        if self.gate is not None:
            self.gate.wait(2)
        return out

    def test_an_older_folder_of_that_name_is_left_alone(self):
        (self.dir / "Final").mkdir()
        (self.dir / "Final" / "old.mp3").write_bytes(b"x")
        ExportMixin._write_bundle(self.host, self.dir, [("Final", self._write)],
                                  [], own_folder=False)
        self.assertEqual(sorted(p.name for p in (self.dir / "Final").iterdir()),
                         ["old.mp3"])
        self.assertTrue((self.dir / "Final_2").is_dir())

    def test_cancel_takes_back_only_what_it_wrote(self):
        (self.dir / "mine.txt").write_text("keep", encoding="utf-8")
        self.gate = threading.Event()

        def cancel():
            if not self.writing.is_set():
                QTimer.singleShot(10, cancel)
                return
            _FakeBusy.last.cancel_requested.emit()
            self.gate.set()

        QTimer.singleShot(50, cancel)
        with mock.patch.object(main_export, "BusyDialog", _FakeBusy):
            ExportMixin._write_bundle(self.host, self.dir,
                                      [("Final", self._write), ("Rest", self._write)],
                                      [], own_folder=False)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["mine.txt"])


if __name__ == "__main__":
    unittest.main()
